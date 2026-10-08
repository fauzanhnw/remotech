from collections import Counter
from datetime import datetime, time, timedelta, timezone as dt_tz
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from server.apps.remotech.mixins import AssignUserMixin, CourseOwnerMixin
from server.apps.remotech.models import (
    Assignment,
    Badge,
    Course,
    CourseEnrollment,
    CourseModule,
    CourseOrder,
    ContentViewed,
    Leaderboard,
    LeaderboardDetail,
    ModuleContent,
    Question,
    Submission,
    UserAnswer,
    UserBadge,
    UserProgress,
)
from server.apps.remotech.serializers import (
    AssignmentSerializer,
    BadgeSerializer,
    ChangePasswordSerializer,
    CourseEnrollmentSerializer,
    CourseModuleSerializer,
    CourseOrderSerializer,
    CourseSerializer,
    CurrentUserSerializer,
    DocumentUploadSerializer,
    EnrollCourseSerializer,
    ForgotPasswordSerializer,
    ImageUploadSerializer,
    LeaderboardDetailSerializer,
    LeaderboardSerializer,
    ModuleContentSerializer,
    MyLeaderboardSerializer,
    ProfileUpdateSerializer,
    QuestionSerializer,
    RegisterSerializer,
    SetPasswordSerializer,
    SubmissionSerializer,
    UserAnswerSerializer,
    UserBadgeSerializer,
    UserProgressSerializer,
)
from server.apps.remotech.services.auth import (
    forgot_password,
    register_user,
    reset_password,
    set_password,
)
from server.apps.remotech.services.grading import (
    compute_auto_score,
    count_correct_answers,
    derive_submission_module_id,
    quiz_submission_scores,
    split_points,
    submission_module,
    upload_submission_scores,
)
from server.apps.remotech.services.payment import (
    check_payment_status,
    enroll_course,
    handle_notification,
)
from server.apps.remotech.services.richtext import extract_media_urls

# Zona "hari" untuk streak belajar: WIB (UTC+7). Indonesia tidak punya DST,
# jadi fixed offset aman dan tidak butuh paket tzdata.
ACTIVITY_TIME_ZONE = dt_tz(timedelta(hours=7))
# Riwayat yang dibaca untuk current/best streak (grafik tetap 7 hari terakhir).
STREAK_LOOKBACK_DAYS = 365


def media_url(storage_name):
    path = f"{settings.MEDIA_URL}{storage_name}"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{settings.BASE_URL.rstrip('/')}{path}"


def login_url():
    return f"{settings.FE_URL.rstrip('/')}/login"


class UserViewSet(viewsets.ViewSet):
    """Profil user login: baca/ubah `/user/me/` dan ganti password."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        if request.method == "PATCH":
            serializer = ProfileUpdateSerializer(
                instance=request.user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(CurrentUserSerializer(request.user).data)

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"message": "Password updated successfully."})


class BadgeViewSet(viewsets.ModelViewSet):
    queryset = Badge.objects.order_by("id")
    serializer_class = BadgeSerializer


class UserBadgeViewSet(viewsets.ModelViewSet):
    queryset = UserBadge.objects.order_by("id")
    serializer_class = UserBadgeSerializer


class CourseViewSet(AssignUserMixin, viewsets.ModelViewSet):
    queryset = Course.objects.order_by("id")
    serializer_class = CourseSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "is_open": ["exact"],
        "is_publish": ["exact"],
        "price": ["lte", "gt"],
    }
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "price", "title"]
    ordering = "-created_at"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"])
    def my(self, request):
        """Daftar course milik request.user — untuk dashboard mentor."""
        queryset = self.filter_queryset(Course.objects.filter(user=request.user))
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def perform_update(self, serializer):
        if serializer.instance.user_id != self.request.user.pk:
            self.permission_denied(
                self.request, message="You do not own this course."
            )
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.pk:
            self.permission_denied(
                self.request, message="You do not own this course."
            )
        instance.delete()


class CourseModuleViewSet(CourseOwnerMixin, viewsets.ModelViewSet):
    queryset = (
        CourseModule.objects.select_related("course").order_by("course", "sequence")
    )
    serializer_class = CourseModuleSerializer
    filterset_fields = ["course"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_course(self, instance=None, validated_data=None):
        if validated_data is not None and "course" in validated_data:
            return validated_data["course"]
        return instance.course if instance is not None else None

    @action(detail=True, methods=["post"], url_path="quiz/start")
    def quiz_start(self, request, pk=None):
        """Buka/resume quiz: draft submission + jawaban yang sudah tersimpan.

        Draft kosong diadopsi agar id submission stabil antar start; draft
        kosong yang tidak terpakai dibuang agar tidak menumpuk.
        """
        module = self.get_object()
        if module.module_category != CourseModule.Category.QUIZ:
            raise ValidationError({"module": ["Bukan module quiz."]})
        if not CourseEnrollment.objects.filter(
            user=request.user, course=module.course
        ).exists():
            raise ValidationError(
                {"course": ["You are not enrolled in this course."]}
            )

        questions = list(
            module.question_set.prefetch_related("questionoption_set").order_by(
                "sequence", "id"
            )
        )
        if not questions:
            raise ValidationError({"module": ["Quiz belum memiliki soal."]})

        submission, empty_drafts = find_quiz_submission(request.user, module)
        if empty_drafts:
            Submission.objects.filter(
                id__in=[draft.pk for draft in empty_drafts]
            ).delete()
        if submission is None:
            submission = Submission.objects.create(
                user=request.user,
                assignment=None,
                submission_url="",
                score=0,
                reviewed_by="",
            )

        completed = bool(submission.reviewed_by)
        payload = quiz_result_payload(submission, questions, reveal=completed)
        payload["completed"] = completed
        if completed:
            payload["result"] = quiz_result_summary(submission, questions, module)
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="quiz/submit")
    def quiz_submit(self, request, pk=None):
        """Selesaikan quiz: semua soal wajib terjawab, lalu skor dihitung.

        Bagian pilihan dinilai otomatis (`reviewed_by="system"` bila tanpa
        essay); module ber-essay menyisakan `reviewed_by` kosong sampai mentor
        menilai lewat `POST /submission/{id}/grade-essay/`.
        """
        module = self.get_object()
        if module.module_category != CourseModule.Category.QUIZ:
            raise ValidationError({"module": ["Bukan module quiz."]})
        if not CourseEnrollment.objects.filter(
            user=request.user, course=module.course
        ).exists():
            raise ValidationError(
                {"course": ["You are not enrolled in this course."]}
            )

        submission_id = request.data.get("submission")
        if not submission_id:
            raise ValidationError(
                {"submission": ["This field is required."]}
            )
        submission = get_object_or_404(
            Submission,
            pk=submission_id,
            user=request.user,
            assignment__isnull=True,
        )
        if submission.reviewed_by:
            raise ValidationError(
                {"submission": ["Quiz sudah pernah disubmit."]}
            )
        module_id = derive_submission_module_id(submission)
        if module_id is not None and module_id != module.pk:
            raise ValidationError(
                {"submission": ["Submission ini bukan untuk module tersebut."]}
            )

        questions = list(
            module.question_set.prefetch_related("questionoption_set").order_by(
                "sequence", "id"
            )
        )
        if not questions:
            raise ValidationError({"module": ["Quiz belum memiliki soal."]})

        answered_ids = set(
            UserAnswer.objects.filter(submission=submission).values_list(
                "question_id", flat=True
            )
        )
        missing = [question.pk for question in questions if question.pk not in answered_ids]
        if missing:
            raise ValidationError(
                {
                    "answers": [
                        "Lengkapi semua jawaban sebelum mengumpulkan quiz. "
                        f"Masih ada {len(missing)} soal yang belum dijawab."
                    ]
                }
            )

        weights = split_points(module, questions)
        correct = count_correct_answers(submission, questions)
        auto_score = compute_auto_score(weights, correct)
        has_essay = weights.essay_count > 0

        submission.score = auto_score
        submission.reviewed_by = "" if has_essay else "system"
        submission.save(update_fields=["score", "reviewed_by"])

        UserProgress.objects.update_or_create(
            module=module,
            user=request.user,
            defaults={
                "status": UserProgress.ProgressStatus.FINISH,
                "complete_at": timezone.now(),
            },
        )
        sync_leaderboard(request.user, module.course)

        payload = quiz_result_payload(submission, questions, reveal=True)
        payload["completed"] = True
        payload["result"] = quiz_result_summary(submission, questions, module)
        return Response(payload)


class ModuleContentViewSet(CourseOwnerMixin, viewsets.ModelViewSet):
    queryset = ModuleContent.objects.select_related(
        "module", "module__course"
    ).order_by("module", "sequence", "id")
    serializer_class = ModuleContentSerializer
    filterset_fields = ["module"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_course(self, instance=None, validated_data=None):
        if validated_data is not None and "module" in validated_data:
            return validated_data["module"].course
        return instance.module.course if instance is not None else None

    def perform_update(self, serializer):
        old_urls = extract_media_urls(serializer.instance.content_text)
        super().perform_update(serializer)
        self.cleanup_media(
            old_urls - extract_media_urls(serializer.instance.content_text)
        )

    def perform_destroy(self, instance):
        old_urls = extract_media_urls(instance.content_text)
        super().perform_destroy(instance)
        self.cleanup_media(old_urls)

    @staticmethod
    def cleanup_media(candidate_urls):
        if not candidate_urls:
            return

        referenced = set()
        for content_text in ModuleContent.objects.values_list(
            "content_text", flat=True
        ):
            referenced |= extract_media_urls(content_text)

        media_prefix = settings.MEDIA_URL.lstrip("/")
        for url in candidate_urls - referenced:
            name = url.lstrip("/")
            if not name.startswith(media_prefix):
                continue
            name = name[len(media_prefix) :]
            if default_storage.exists(name):
                default_storage.delete(name)


class CourseOrderViewSet(viewsets.ModelViewSet):
    queryset = CourseOrder.objects.select_related("course").order_by("id")
    serializer_class = CourseOrderSerializer
    filterset_fields = ["course", "user", "transaction_status"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        return queryset.filter(user=user)

    def get_permissions(self):
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    @action(methods=["post"], detail=False)
    def enroll(self, request):
        serializer = EnrollCourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order, enrolled = enroll_course(
            request.user, serializer.validated_data["course"]
        )
        return Response(
            {
                "order": CourseOrderSerializer(order).data,
                "enrolled": enrolled,
                "snap_token": order.snap_token,
            },
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True, url_path="check-payment")
    def check_payment(self, request, pk=None):
        order = self.get_object()
        order = check_payment_status(order)
        return Response(CourseOrderSerializer(order).data)


class CourseEnrollmentViewSet(viewsets.ModelViewSet):
    queryset = CourseEnrollment.objects.order_by("id")
    serializer_class = CourseEnrollmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["course", "user"]
    search_fields = ["course__title"]
    ordering_fields = ["enrolled_at"]
    ordering = "-enrolled_at"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        return queryset.filter(user=user)

    def create(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)


def sync_leaderboard(user, course):
    """Recompute total poin + detail leaderboard user dari progress `finish`.

    Idempoten — aman dipanggil berulang, termasuk siklus batalkan→tandai lagi.
    Module text/video memberi `module.point` penuh; module upload/quiz memberi
    skor submission terakhirnya (0 bila belum ada atau belum dinilai).
    """
    finished = UserProgress.objects.filter(
        user=user,
        module__course=course,
        status=UserProgress.ProgressStatus.FINISH,
    )
    finished_ids = list(finished.values_list("module_id", flat=True))
    upload_scores = upload_submission_scores(user)
    quiz_scores = quiz_submission_scores(user)

    points_by_module = {}
    for module in CourseModule.objects.filter(id__in=finished_ids):
        if module.module_category == CourseModule.Category.UPLOAD:
            point = upload_scores.get(module.id, 0)
        elif module.module_category == CourseModule.Category.QUIZ:
            point = quiz_scores.get(module.id, 0)
        else:
            point = module.point
        points_by_module[module.id] = point

    total_points = sum(points_by_module.values())
    leaderboard, _ = Leaderboard.objects.get_or_create(
        user=user, course=course, defaults={"total_points": total_points}
    )
    if leaderboard.total_points != total_points:
        leaderboard.total_points = total_points
        leaderboard.save(update_fields=["total_points"])

    LeaderboardDetail.objects.filter(leaderboard=leaderboard).exclude(
        module_id__in=finished_ids
    ).delete()
    for module_id, point in points_by_module.items():
        module = CourseModule.objects.get(pk=module_id)
        detail, created = LeaderboardDetail.objects.get_or_create(
            leaderboard=leaderboard,
            module=module,
            defaults={"description": module.title, "point": point},
        )
        if not created and detail.point != point:
            detail.point = point
            detail.save(update_fields=["point"])
    return leaderboard


class UserProgressViewSet(viewsets.ModelViewSet):
    queryset = UserProgress.objects.order_by("id")
    serializer_class = UserProgressSerializer

    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user)
        course = self.request.query_params.get("course")
        if course:
            queryset = queryset.filter(module__course=course)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        module = serializer.validated_data["module"]
        enrolled = CourseEnrollment.objects.filter(
            user=request.user, course=module.course
        ).exists()
        if not enrolled:
            raise ValidationError({"course": ["You are not enrolled in this course."]})
        if module.module_category in (
            CourseModule.Category.UPLOAD,
            CourseModule.Category.QUIZ,
        ):
            raise ValidationError(
                {
                    "module": [
                        "Module upload/quiz diselesaikan lewat pengumpulan "
                        "tugas atau pengerjaan quiz, bukan penandaan manual."
                    ]
                }
            )
        progress, _ = UserProgress.objects.update_or_create(
            module=module,
            user=request.user,
            defaults={
                "status": UserProgress.ProgressStatus.FINISH,
                "complete_at": timezone.now(),
            },
        )
        sync_leaderboard(request.user, module.course)
        return Response(self.get_serializer(progress).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        progress = self.get_object()
        module = progress.module
        self.perform_destroy(progress)
        sync_leaderboard(request.user, module.course)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        course_ids = (
            CourseEnrollment.objects.filter(user=request.user)
            .values_list("course_id", flat=True)
            .distinct()
        )
        finished_counts = Counter(
            UserProgress.objects.filter(
                user=request.user,
                status=UserProgress.ProgressStatus.FINISH,
            ).values_list("module__course_id", flat=True)
        )
        rows = []
        for course_id in course_ids:
            total = CourseModule.objects.filter(course_id=course_id).count()
            completed = finished_counts.get(course_id, 0)
            rows.append(
                {
                    "course": course_id,
                    "total": total,
                    "completed": completed,
                    "percent": round(completed / total * 100) if total else 0,
                }
            )
        return Response(rows)

    @action(detail=False, methods=["get"], url_path="activity")
    def activity(self, request):
        """GET /progress/activity/ — grafik 7 hari + streak belajar.

        Hari aktif = ada konten dibuka (`ContentViewed.viewed_at`), module
        selesai (`UserProgress.complete_at`) atau tugas/quiz dikumpulkan
        (`Submission.submit_on`) pada hari yang sama (zona WIB). `days` selalu
        berisi 7 hari terakhir (terakhir = hari ini); `current_streak` boleh
        berawal dari kemarin bila hari ini belum ada aktivitas.
        """
        user = request.user
        today = timezone.localtime(timezone.now(), ACTIVITY_TIME_ZONE).date()
        window_start = datetime.combine(
            today - timedelta(days=STREAK_LOOKBACK_DAYS - 1),
            time.min,
            tzinfo=ACTIVITY_TIME_ZONE,
        )

        def local_date(value):
            return timezone.localtime(value, ACTIVITY_TIME_ZONE).date()

        sources = (
            ContentViewed.objects.filter(user=user, viewed_at__gte=window_start)
            .values_list("viewed_at", flat=True),
            UserProgress.objects.filter(user=user, complete_at__gte=window_start)
            .values_list("complete_at", flat=True),
            Submission.objects.filter(user=user, submit_on__gte=window_start)
            .values_list("submit_on", flat=True),
        )
        counts = Counter()
        for timestamps in sources:
            for value in timestamps.iterator():
                counts[local_date(value)] += 1
        active_dates = set(counts)

        current_streak = 0
        day = today if today in active_dates else today - timedelta(days=1)
        while day in active_dates:
            current_streak += 1
            day -= timedelta(days=1)

        best_streak = run = 0
        day = today - timedelta(days=STREAK_LOOKBACK_DAYS - 1)
        while day <= today:
            if day in active_dates:
                run += 1
                best_streak = max(best_streak, run)
            else:
                run = 0
            day += timedelta(days=1)

        days = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            days.append(
                {
                    "date": day.isoformat(),
                    "weekday": day.weekday(),
                    "active": day in active_dates,
                    "count": counts.get(day, 0),
                }
            )

        return Response(
            {
                "days": days,
                "current_streak": current_streak,
                "best_streak": best_streak,
                "week_active_count": sum(1 for entry in days if entry["active"]),
            }
        )


class ContentViewMarkView(APIView):
    """POST /content-view/<content_id>/ — tandai konten sudah dibuka (idempoten).

    Module text/video baru otomatis `finish` (+ sinkron leaderboard) setelah
    SELURUH kontennya dilihat, bukan konten pertama. Module upload/quiz tidak
    pernah auto-finish lewat sini (submit tugas / tombol manual).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, content_id):
        content = get_object_or_404(ModuleContent, pk=content_id)
        ContentViewed.objects.get_or_create(user=request.user, content=content)

        module = content.module
        if module.module_category not in (
            CourseModule.Category.TEXT,
            CourseModule.Category.VIDEO,
        ):
            return Response({"module_completed": False})

        enrolled = CourseEnrollment.objects.filter(
            user=request.user, course=module.course
        ).exists()
        already_finished = UserProgress.objects.filter(
            module=module,
            user=request.user,
            status=UserProgress.ProgressStatus.FINISH,
        ).exists()
        total_contents = ModuleContent.objects.filter(module=module).count()
        viewed_count = ContentViewed.objects.filter(
            user=request.user, content__module=module
        ).count()

        if not enrolled or already_finished or not total_contents:
            return Response({"module_completed": False})
        if viewed_count < total_contents:
            return Response({"module_completed": False})

        UserProgress.objects.update_or_create(
            module=module,
            user=request.user,
            defaults={
                "status": UserProgress.ProgressStatus.FINISH,
                "complete_at": timezone.now(),
            },
        )
        sync_leaderboard(request.user, module.course)
        return Response({"module_completed": True})


class ContentViewListView(APIView):
    """GET /content-view/?course=<id> — konten sudah-dibuka milik sendiri."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        contents = ContentViewed.objects.filter(user=request.user)
        course = request.query_params.get("course")
        if course:
            contents = contents.filter(content__module__course=course)
        return Response(
            {"content_ids": list(contents.values_list("content_id", flat=True))}
        )


class AssignmentViewSet(CourseOwnerMixin, viewsets.ModelViewSet):
    """Pengumpulan penugasan module `upload`.

    Mentor membuat assignment lewat "Add Content" (hanya pemilik course);
    student lalu mengumpulkan tautan hasil kerjanya sebagai Submission.
    """

    queryset = Assignment.objects.select_related(
        "course_module", "course_module__course"
    ).order_by("id")
    serializer_class = AssignmentSerializer
    filterset_fields = ["course_module"]

    def get_course(self, instance=None, validated_data=None):
        if validated_data is not None and "course_module" in validated_data:
            return validated_data["course_module"].course
        return instance.course_module.course if instance is not None else None


class QuestionViewSet(CourseOwnerMixin, viewsets.ModelViewSet):
    """Soal + opsi jawaban module quiz (nested `options`).

    List/retrieve publik untuk login; `is_correct`/`explanation` hanya
    di-reveal ke pemilik course (lihat QuestionSerializer).
    """

    queryset = (
        Question.objects.select_related("module", "module__course")
        .prefetch_related("questionoption_set")
        .order_by("module", "sequence", "id")
    )
    serializer_class = QuestionSerializer
    filterset_fields = ["module"]

    def get_course(self, instance=None, validated_data=None):
        if validated_data is not None and "module" in validated_data:
            return validated_data["module"].course
        return instance.module.course if instance is not None else None

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["reveal"] = self._reveal_correctness()
        return context

    def _reveal_correctness(self):
        """Kunci jawaban hanya untuk pemilik course module terkait."""
        user = self.request.user
        if not user or not user.is_authenticated:
            return False

        module = None
        module_id = self.request.query_params.get("module")
        if module_id and str(module_id).isdigit():
            module = CourseModule.objects.filter(pk=int(module_id)).first()
        elif self.action == "retrieve":
            question = Question.objects.filter(pk=self.kwargs.get("pk")).first()
            module = question.module if question else None
        if module is None:
            return False
        return module.course.user_id == user.pk

    def perform_destroy(self, instance):
        if UserAnswer.objects.filter(question__module=instance.module).exists():
            raise ValidationError(
                {"detail": ["Quiz sudah ada pengerjaan — soal tidak bisa dihapus."]}
            )
        super().perform_destroy(instance)


class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    """Papan skor per course + ringkasan poin milik sendiri (`/leaderboard/me/`)."""

    queryset = Leaderboard.objects.select_related("user", "course").order_by(
        "-total_points", "id"
    )
    serializer_class = LeaderboardSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["course", "user"]
    ordering_fields = ["total_points", "id"]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """GET /leaderboard/me/ — total poin + per-course (judul, rank, peserta).

        Course yang di-enroll selalu ikut (poin 0, `rank` null bila belum
        pernah menyelesaikan module); urutan: poin tertinggi dulu.
        """
        user = request.user
        enrollments = list(
            CourseEnrollment.objects.filter(user=user).select_related("course")
        )
        course_ids = [entry.course_id for entry in enrollments]

        my_points = {
            row.course_id: row.total_points
            for row in Leaderboard.objects.filter(user=user)
        }

        counts = Counter()
        ranks = {}
        rows = (
            Leaderboard.objects.filter(course_id__in=course_ids)
            .order_by("course_id", "-total_points", "id")
            .values_list("course_id", "user_id")
        )
        for course_id, row_user_id in rows:
            counts[course_id] += 1
            if row_user_id == user.pk:
                ranks[course_id] = counts[course_id]

        courses = [
            {
                "course": entry.course_id,
                "course_title": entry.course.title,
                "total_points": my_points.get(entry.course_id, 0),
                "rank": ranks.get(entry.course_id),
                "participants": counts.get(entry.course_id, 0),
            }
            for entry in enrollments
        ]
        courses.sort(key=lambda item: (-item["total_points"], item["course_title"]))

        serializer = MyLeaderboardSerializer(
            {
                "total_points": sum(my_points.get(course_id, 0) for course_id in course_ids),
                "courses": courses,
            }
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def details(self, request, pk=None):
        """GET /leaderboard/{id}/details/ — rincian poin per module satu peserta."""
        leaderboard = self.get_object()
        rows = LeaderboardDetail.objects.filter(leaderboard=leaderboard).order_by(
            "module__sequence", "id"
        )
        return Response(LeaderboardDetailSerializer(rows, many=True).data)


def find_quiz_submission(user, module):
    """(submission quiz user untuk module, draft-tanpa-jawaban sisanya).

    Module submission quiz diturunkan dari jawabannya. Draft yang belum punya
    jawaban sama sekali belum bisa diidentifikasi module-nya — bila belum ada
    submission untuk module ini, draft kosong pertama diadopsi (bukan membuat
    baru) supaya id submission stabil antar start; sisanya dibuang.
    """
    found = None
    empty_drafts = []
    candidates = Submission.objects.filter(
        user=user, assignment__isnull=True
    ).order_by("id")
    for submission in candidates:
        module_id = derive_submission_module_id(submission)
        if module_id == module.pk:
            found = submission
        elif module_id is None:
            empty_drafts.append(submission)

    if found is None and empty_drafts:
        found = empty_drafts.pop(0)
    return found, empty_drafts


def quiz_result_payload(submission, questions, reveal):
    return {
        "submission": SubmissionSerializer(submission).data,
        "questions": QuestionSerializer(
            questions, many=True, context={"reveal": reveal}
        ).data,
        "answers": UserAnswerSerializer(
            UserAnswer.objects.filter(submission=submission), many=True
        ).data,
    }


def quiz_result_summary(submission, questions, module):
    """Ringkasan skor quiz untuk response start (sudah selesai) & submit."""
    weights = split_points(module, questions)
    correct = count_correct_answers(submission, questions)
    return {
        "score": submission.score,
        "max_score": module.point,
        "auto_score": compute_auto_score(weights, correct),
        "auto_max": weights.auto_max,
        "essay_max": weights.essay_max,
        "correct": correct,
        "auto_total": weights.auto_count,
        "essay_count": weights.essay_count,
        # Essay ditahan sampai mentor menilai (reviewed_by masih kosong).
        "pending": weights.essay_count > 0 and submission.reviewed_by == "",
    }


class SubmissionViewSet(viewsets.ModelViewSet):
    """Submission tugas (assignment) & hasil quiz (tanpa assignment).

    Pembacaan: submission milik sendiri atau submission course milik
    request.user (mentor). Penilaian tugas lewat PATCH `score` (maksimal
    poin module); penilaian essay quiz lewat action `grade-essay`.
    """

    queryset = Submission.objects.select_related(
        "user",
        "assignment",
        "assignment__course_module",
        "assignment__course_module__course",
    )
    serializer_class = SubmissionSerializer
    filterset_fields = ["assignment", "user"]

    def get_queryset(self):
        # module diturunkan dari jawaban quiz (assignment kosong)
        queryset = (
            super()
            .get_queryset()
            .annotate(
                derived_module=Subquery(
                    CourseModule.objects.filter(
                        question__useranswer__submission=OuterRef("pk")
                    ).values("id")[:1]
                ),
                derived_module_title=Subquery(
                    CourseModule.objects.filter(
                        question__useranswer__submission=OuterRef("pk")
                    ).values("title")[:1]
                ),
                derived_module_point=Subquery(
                    CourseModule.objects.filter(
                        question__useranswer__submission=OuterRef("pk")
                    ).values("point")[:1]
                ),
                derived_course=Subquery(
                    CourseModule.objects.filter(
                        question__useranswer__submission=OuterRef("pk")
                    ).values("course_id")[:1]
                ),
                derived_course_title=Subquery(
                    CourseModule.objects.filter(
                        question__useranswer__submission=OuterRef("pk")
                    ).values("course__title")[:1]
                ),
            )
            .order_by("id")
        )

        user = self.request.user
        if not user.is_superuser:
            own_modules = CourseModule.objects.filter(
                course__user=user
            ).values_list("id", flat=True)
            queryset = queryset.filter(
                Q(user=user)
                | Q(assignment__course_module_id__in=own_modules)
                | Q(derived_module__in=own_modules)
            )

        params = self.request.query_params
        module = params.get("module")
        if module and str(module).isdigit():
            queryset = queryset.filter(
                Q(assignment__course_module_id=int(module))
                | Q(derived_module=int(module))
            )
        course = params.get("course")
        if course and str(course).isdigit():
            course_modules = CourseModule.objects.filter(
                course_id=int(course)
            ).values_list("id", flat=True)
            queryset = queryset.filter(
                Q(assignment__course_module_id__in=course_modules)
                | Q(derived_module__in=course_modules)
            )
        graded = params.get("graded")
        if graded == "true":
            queryset = queryset.exclude(reviewed_by="")
        elif graded == "false":
            queryset = queryset.filter(reviewed_by="")

        return queryset

    def perform_create(self, serializer):
        assignment = serializer.validated_data["assignment"]
        module = assignment.course_module
        user = self.request.user

        # Satu submission per (assignment, user): submit ulang memperbarui
        # tautan selama belum dinilai.
        existing = Submission.objects.filter(user=user, assignment=assignment).first()
        if existing is not None and existing.reviewed_by:
            raise ValidationError(
                {
                    "assignment": [
                        "Tugas sudah dinilai dan tidak bisa dikumpulkan ulang."
                    ]
                }
            )
        serializer.instance = existing
        submission = serializer.save(user=user, score=0, reviewed_by="")

        if CourseEnrollment.objects.filter(user=user, course=module.course).exists():
            # Submit tugas = otomatis menandai module selesai.
            UserProgress.objects.update_or_create(
                module=module,
                user=user,
                defaults={
                    "status": UserProgress.ProgressStatus.FINISH,
                    "complete_at": timezone.now(),
                },
            )
            sync_leaderboard(user, module.course)

    def perform_update(self, serializer):
        submission = serializer.instance
        user = self.request.user
        fields = set(serializer.validated_data)

        if fields & {"score", "reviewed_by"}:
            # Jalur penilaian mentor.
            module = submission_module(submission)
            if module is None or module.course.user_id != user.pk:
                self.permission_denied(
                    self.request, message="You do not own this course."
                )
            if fields - {"score", "reviewed_by"}:
                raise ValidationError(
                    {
                        "detail": [
                            "Saat menilai, hanya score dan reviewed_by "
                            "yang boleh diubah."
                        ]
                    }
                )
            if submission.assignment_id is None:
                raise ValidationError(
                    {"detail": ["Submission quiz dinilai lewat grade-essay."]}
                )
            serializer.save(reviewed_by=user.username[:50])
            sync_leaderboard(submission.user, module.course)
            return

        # Jalur student: memperbarui tautan tugas milik sendiri.
        if submission.user_id != user.pk:
            self.permission_denied(
                self.request, message="You can only update your own submission."
            )
        if fields - {"submission_url"}:
            raise ValidationError(
                {"detail": ["Hanya submission_url yang bisa diperbarui."]}
            )
        if submission.reviewed_by:
            raise ValidationError(
                {"detail": ["Submission sudah dinilai dan tidak bisa diubah."]}
            )
        if submission.assignment_id is None:
            raise ValidationError(
                {"detail": ["Submission quiz tidak bisa diubah manual."]}
            )
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        module = submission_module(instance)
        is_course_owner = module is not None and module.course.user_id == user.pk
        if instance.user_id != user.pk and not is_course_owner:
            self.permission_denied(self.request, message="Not allowed.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="grade-essay")
    def grade_essay(self, request, pk=None):
        """Mentor menilai jawaban essay submission quiz → skor final.

        Skor otomatis (bagian pilihan) dihitung ulang dari jawaban, sehingga
        penilaian ulang idempoten. Total akhir dibatasi poin maksimal module.
        """
        submission = self.get_object()
        if submission.assignment_id is not None:
            raise ValidationError(
                {"detail": ["Submission tugas dinilai lewat PATCH score."]}
            )

        module = submission_module(submission)
        if module is None:
            raise ValidationError(
                {"detail": ["Submission quiz belum memiliki jawaban."]}
            )
        if module.course.user_id != request.user.pk:
            self.permission_denied(request, message="You do not own this course.")

        items = request.data.get("answers")
        if not isinstance(items, list) or not items:
            raise ValidationError(
                {"answers": ["Setidaknya satu jawaban essay harus dinilai."]}
            )

        questions = list(module.question_set.all())
        weights = split_points(module, questions)
        if weights.essay_count == 0:
            raise ValidationError(
                {"answers": ["Module ini tidak memiliki soal essay."]}
            )

        answered_ids = set(
            UserAnswer.objects.filter(submission=submission).values_list(
                "question_id", flat=True
            )
        )
        if not {question.pk for question in questions}.issubset(answered_ids):
            raise ValidationError(
                {"detail": ["Quiz belum disubmit, tidak bisa dinilai."]}
            )
        if not UserProgress.objects.filter(
            module=module, user=submission.user
        ).exists():
            raise ValidationError(
                {"detail": ["Quiz belum disubmit, tidak bisa dinilai."]}
            )

        essay_answers = {
            answer.pk: answer
            for answer in UserAnswer.objects.filter(
                submission=submission,
                question__question_type=Question.QuestionType.ESSAI,
            )
        }
        graded = {}
        for item in items:
            if not isinstance(item, dict):
                raise ValidationError(
                    {"answers": ["Format data penilaian tidak valid."]}
                )
            answer_id = item.get("id")
            score = item.get("score")
            if answer_id not in essay_answers:
                raise ValidationError(
                    {
                        "answers": [
                            "Hanya jawaban essay milik submission ini yang "
                            "bisa dinilai."
                        ]
                    }
                )
            if answer_id in graded:
                raise ValidationError(
                    {"answers": ["Terdapat jawaban ganda dalam data penilaian."]}
                )
            if isinstance(score, bool) or not isinstance(score, int) or score < 0:
                raise ValidationError(
                    {"answers": ["Nilai harus bilangan bulat lebih besar atau sama dengan 0."]}
                )
            graded[answer_id] = score

        if set(graded) != set(essay_answers):
            raise ValidationError(
                {"answers": ["Semua jawaban essay harus dinilai."]}
            )

        auto_score = compute_auto_score(
            weights, count_correct_answers(submission, questions)
        )
        final_score = auto_score + sum(graded.values())
        if final_score > module.point:
            raise ValidationError(
                {
                    "answers": [
                        f"Total nilai melebihi poin maksimal module ({module.point})."
                    ]
                }
            )

        for answer_id, score in graded.items():
            UserAnswer.objects.filter(pk=answer_id).update(score=score)
        submission.score = final_score
        submission.reviewed_by = request.user.username[:50]
        submission.save(update_fields=["score", "reviewed_by"])
        if CourseEnrollment.objects.filter(
            user=submission.user, course=module.course
        ).exists():
            sync_leaderboard(submission.user, module.course)
        return Response(SubmissionSerializer(submission).data)


class UserAnswerViewSet(viewsets.ModelViewSet):
    """Simpan jawaban quiz per soal (upsert per submission + soal)."""

    queryset = UserAnswer.objects.select_related(
        "submission", "question", "question_option"
    ).order_by("question__sequence", "question__id")
    serializer_class = UserAnswerSerializer
    filterset_fields = ["submission", "question"]

    def get_queryset(self):
        return super().get_queryset().filter(submission__user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Instance diisi sebelum validasi agar UniqueTogetherValidator
        # mengabaikan baris lama → POST ulang = upsert, bukan 400.
        existing = None
        submission_id = request.data.get("submission")
        question_id = request.data.get("question")
        if submission_id and question_id:
            existing = self.get_queryset().filter(
                submission_id=submission_id, question_id=question_id
            ).first()
        serializer = self.get_serializer(data=request.data, instance=existing)
        serializer.is_valid(raise_exception=True)
        answer = serializer.save()
        return Response(
            self.get_serializer(answer).data, status=status.HTTP_201_CREATED
        )

    def perform_destroy(self, instance):
        if instance.submission.user_id != self.request.user.pk:
            self.permission_denied(self.request, message="Not allowed.")
        if instance.submission.reviewed_by:
            raise ValidationError(
                {"detail": ["Quiz sudah disubmit dan jawaban tidak bisa dihapus."]}
            )
        instance.delete()


class ImageUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.validated_data["image"]
        name = default_storage.save(f"course-content/images/{uuid4().hex}.webp", image)
        return Response({"url": media_url(name)}, status=status.HTTP_201_CREATED)


class DocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.validated_data["file"]
        extension = serializer.validated_data["extension"]
        name = default_storage.save(
            f"course-content/documents/{uuid4().hex}.{extension}", document
        )
        return Response({"url": media_url(name)}, status=status.HTTP_201_CREATED)


class RegisterViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def create(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        register_user(**serializer.validated_data)
        return Response(
            {
                "message": "Registration successful. Please check your email to set your password."
            },
            status=status.HTTP_201_CREATED,
        )


class SetPasswordViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        return render(request, "set_password.html", {"login_url": login_url()})

    def create(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        set_password(token=data["token"], password=data["password"])
        return Response(
            {"message": "Password set successfully. You can now login."},
            status=status.HTTP_200_OK,
        )


class TokenObtainPairViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def create(self, request):
        view = TokenObtainPairView.as_view()
        return view(request._request)


class TokenRefreshViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def create(self, request):
        view = TokenRefreshView.as_view()
        return view(request._request)


class ForgotPasswordViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def create(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        forgot_password(**serializer.validated_data)
        return Response(
            {
                "message": "If your email is registered, you will receive a password reset link."
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordResetViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def create(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        reset_password(token=data["token"], password=data["password"])
        return Response(
            {"message": "Password reset successfully. You can now login."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordPageView(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        return render(request, "reset_password.html", {"login_url": login_url()})


class MidtransNotificationView(APIView):
    """Midtrans payment notification webhook (configured in Midtrans dashboard)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        order = handle_notification(request.data)
        return Response(CourseOrderSerializer(order).data, status=status.HTTP_200_OK)
