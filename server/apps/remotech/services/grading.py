"""Pembagian bobot poin quiz, derivasi module submission, dan skoring.

Module quiz tidak menyimpan FK module di `Submission` — module diturunkan
lewat jawaban `UserAnswer -> Question -> module`. Submission tugas (upload)
punya `assignment` sehingga module-nya langsung diketahui.
"""

from dataclasses import dataclass

from server.apps.remotech.models import CourseModule, Submission, UserAnswer


@dataclass(frozen=True)
class QuizWeights:
    """Pembagian `module.point` untuk satu quiz.

    Setiap soal memperoleh bobot sama; bagian essay ditahan untuk dinilai
    mentor (`essay_max`), bagian pilihan dihitung otomatis (`auto_max`).
    """

    total: int
    auto_count: int
    essay_count: int
    auto_max: int
    essay_max: int


def split_points(module: CourseModule, questions: list | None = None) -> QuizWeights:
    if questions is None:
        questions = list(module.question_set.all())

    total = len(questions)
    essay_count = sum(1 for question in questions if question.is_essay)
    auto_count = total - essay_count
    essay_max = round(module.point * essay_count / total) if total else 0
    auto_max = module.point - essay_max
    return QuizWeights(
        total=total,
        auto_count=auto_count,
        essay_count=essay_count,
        auto_max=auto_max,
        essay_max=essay_max,
    )


def compute_auto_score(weights: QuizWeights, correct_count: int) -> int:
    """Skor bagian pilihan (boolean/choices) dari jumlah jawaban benar."""
    if weights.auto_count == 0:
        return 0
    return round(weights.auto_max * correct_count / weights.auto_count)


def penalized_score(score, is_late, penalty_percent):
    """Poin efektif leaderboard setelah penalti keterlambatan (soft).

    Skor mentah submission tidak diubah — hanya poin yang mengalir ke
    leaderboard yang dikurangi. `is_late` adalah snapshot saat submit
    pertama; penalti 0 berarti telat tetap mendapat poin penuh.
    """
    if not is_late or not penalty_percent:
        return score
    return round(score * (100 - penalty_percent) / 100)


def derive_submission_module_id(submission: Submission) -> int | None:
    """Module milik submission (upload: dari assignment; quiz: dari jawaban).

    Mengembalikan None untuk draft quiz yang belum punya jawaban sama sekali.
    """
    if submission.assignment_id is not None:
        return submission.assignment.course_module_id
    return (
        UserAnswer.objects.filter(submission=submission)
        .values_list("question__module_id", flat=True)
        .first()
    )


def submission_module(submission: Submission) -> CourseModule | None:
    module_id = derive_submission_module_id(submission)
    if module_id is None:
        return None
    return CourseModule.objects.filter(pk=module_id).first()


def count_correct_answers(submission: Submission, questions: list) -> int:
    """Jumlah jawaban benar untuk soal pilihan (essay tidak dihitung)."""
    answer_by_question = {
        answer.question_id: answer
        for answer in UserAnswer.objects.filter(
            submission=submission, question_id__in=[question.pk for question in questions]
        )
    }
    correct = 0
    for question in questions:
        if question.is_essay:
            continue
        answer = answer_by_question.get(question.pk)
        if answer is not None and answer.is_correct:
            correct += 1
    return correct


def quiz_submission_scores(user) -> dict[int, int]:
    """Map `module_id -> skor` dari seluruh submission quiz milik user.

    Baris paling baru per module yang dipakai; module yang belum bisa
    diturunkan (draft tanpa jawaban) diabaikan. Skor yang dikembalikan
    sudah skor efektif (penalti keterlambatan bila submission telat).
    """
    module_by_submission = {}
    for submission_id, module_id in UserAnswer.objects.filter(
        submission__user=user, submission__assignment__isnull=True
    ).values_list("submission_id", "question__module_id"):
        module_by_submission.setdefault(submission_id, module_id)

    scores: dict[int, int] = {}
    if not module_by_submission:
        return scores
    rows = (
        Submission.objects.filter(user=user, assignment__isnull=True)
        .order_by("-id")
        .values_list("id", "score", "is_late")
    )
    latest = {}
    for submission_id, score, is_late in rows:
        module_id = module_by_submission.get(submission_id)
        if module_id is not None and module_id not in latest:
            latest[module_id] = (score, is_late)
    if not latest:
        return scores
    penalties = dict(
        CourseModule.objects.filter(id__in=latest).values_list(
            "id", "late_penalty_percent"
        )
    )
    for module_id, (score, is_late) in latest.items():
        scores[module_id] = penalized_score(
            score, is_late, penalties.get(module_id, 0)
        )
    return scores


def upload_submission_scores(user) -> dict[int, int]:
    """Map `module_id -> skor` dari submission tugas (upload) milik user.

    Baris paling baru per module yang dipakai. Skor yang dikembalikan
    sudah skor efektif (penalti keterlambatan bila submission telat).
    """
    scores: dict[int, int] = {}
    rows = (
        Submission.objects.filter(user=user, assignment__isnull=False)
        .order_by("-id")
        .values_list(
            "assignment__course_module_id",
            "score",
            "is_late",
            "assignment__course_module__late_penalty_percent",
        )
    )
    for module_id, score, is_late, penalty_percent in rows:
        if module_id is not None and module_id not in scores:
            scores[module_id] = penalized_score(score, is_late, penalty_percent)
    return scores
