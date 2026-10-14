import random
from collections import Counter
from datetime import datetime, time, timedelta
from datetime import timezone as dt_tz
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db.models import OuterRef, Q, Subquery, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status, viewsets
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
    ContentViewed,
    Course,
    CourseEnrollment,
    CourseModule,
    CourseOrder,
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
    PointBonusSerializer,
    ProfileUpdateSerializer,
    QuestionSerializer,
    RegisterSerializer,
    SetPasswordSerializer,
    SubmissionSerializer,
    UserAnswerSerializer,
    UserBadgeAwardSerializer,
    UserBadgeSerializer,
    UserProgressSerializer,
)
from server.apps.remotech.services.auth import (
    forgot_password,
    register_user,
    reset_password,
    set_password,
)
from server.apps.remotech.services.badges import sync_badges
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


class BadgeViewSet(CourseOwnerMixin, viewsets.ModelViewSet):
    """Definisi badge per course.

    List/retrieve terbuka (public catalog per course); tulis hanya pemilik
    course. `rule_type` dijaga di serializer — badge `course_complete` dievaluasi
    otomatis oleh `sync_badges`, `manual` diberi mentor lewat /user-badge/.
    """

    queryset = Badge.objects.select_related("course").order_by("id")
    serializer_class = BadgeSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["course", "rule_type"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_course(self, instance=None, validated_data=None):
        if validated_data is not None and "course" in validated_data:
            return validated_data["course"]
        return instance.course if instance is not None else None


def _mentor_display_name(user):
    """Tampilan pemberi badge manual: "Nama Lengkap - email".

    `awarded_by` menyimpan username (= email saat registrasi); tampilan di
    /user-badge/me/ memakai nama lengkap bila ada, fallback email/username.
    """
    full_name = user.get_full_name()
    if full_name and user.email:
        return f"{full_name} - {user.email}"
    return full_name or user.email or user.username


class UserBadgeViewSet(viewsets.ModelViewSet):
    """Badge yang dimiliki user.

    - GET  /user-badge/         — baris milik sendiri (superuser: semua), filter `?course=`
    - GET  /user-badge/me/      — ringkas: badge definition + progress course
    - POST /user-badge/         — mentor award badge `manual` ke student enrolled
    - DELETE /user-badge/{id}/  — cabut (pemilik course badge / superuser)
    """

    queryset = UserBadge.objects.select_related("badge", "badge__course", "user")
    serializer_class = UserBadgeSerializer
    filterset_fields = ["badge", "user", "badge__course"]

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-earned_at", "id")
        user = self.request.user
        if user.is_superuser:
            return queryset
        if self.action in ("destroy", "list"):
            # Revoke & daftar penerima oleh pemilik course badge.
            owned_course_ids = Course.objects.filter(user=user).values_list(
                "id", flat=True
            )
            return queryset.filter(
                Q(user=user) | Q(badge__course_id__in=owned_course_ids)
            )
        return queryset.filter(user=user)

    def create(self, request, *args, **kwargs):
        serializer = UserBadgeAwardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        badge = serializer.validated_data["badge"]
        student = serializer.validated_data["user"]

        if badge.rule_type != Badge.RuleType.MANUAL:
            raise ValidationError(
                {"badge": ["Only manual-type badges can be awarded by a mentor."]}
            )
        if badge.course.user_id != request.user.pk:
            self.permission_denied(
                request, message="You do not own this course."
            )
        if not CourseEnrollment.objects.filter(
            user=student, course=badge.course
        ).exists():
            raise ValidationError(
                {"user": ["Student is not enrolled in this course."]}
            )

        user_badge, created = UserBadge.objects.get_or_create(
            user=student,
            badge=badge,
            defaults={"awarded_by": request.user.username[:50]},
        )
        if not created:
            raise ValidationError({"badge": ["Badge has already been awarded."]})
        return Response(
            self.get_serializer(user_badge).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user_badge = self.get_object()
        badge = user_badge.badge
        if not request.user.is_superuser and badge.course.user_id != request.user.pk:
            self.permission_denied(
                request, message="You do not own this course."
            )
        user_badge.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def earned(self, request):
        """GET /user-badge/earned/?user= — badge yang sudah didapat user tertentu.

        Read-only publik untuk semua user login (modal profil peserta dari
        leaderboard); tanpa pembatasan queryset `get_queryset` biasa. Semua
        baris `UserBadge` sudah earned, sehingga tidak ada baris locked.
        """
        target_id = request.query_params.get("user")
        if not target_id or not str(target_id).isdigit():
            raise ValidationError({"user": ["Query parameter `user` is required."]})
        target = get_object_or_404(User, pk=target_id)
        rows = UserBadge.objects.filter(user=target).select_related(
            "badge", "badge__course"
        )
        return Response(UserBadgeSerializer(rows, many=True).data)

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Badge course yang di-enroll: earned + locked dengan progres.

        Locked = definisi badge pada course yang di-enroll tapi belum dimiliki;
        `progress` = module selesai / total module pada course badge tersebut
        (dipakai frontend menampilkan "x/y" pada badge locked). Badge earned
        menyertakan `earned_at` (ISO) + `awarded_by` ("system" / "Nama Lengkap
        - email" mentor, fallback email/username); locked mengembalikan
        `earned_at` null dan `awarded_by` "".
        """
        enrolled_course_ids = set(
            CourseEnrollment.objects.filter(user=request.user).values_list(
                "course_id", flat=True
            )
        )
        course_param = request.query_params.get("course")
        if course_param and str(course_param).isdigit():
            enrolled_course_ids &= {int(course_param)}

        earned_map = {
            row["badge_id"]: row
            for row in UserBadge.objects.filter(user=request.user).values(
                "badge_id", "earned_at", "awarded_by"
            )
        }
        # awarded_by menyimpan username mentor (= email saat registrasi);
        # tampilkan "Nama Lengkap - email" (fallback nama / email) agar
        # tidak sekadar memperlihatkan email.
        mentor_names = {
            user.username: _mentor_display_name(user)
            for user in User.objects.filter(
                username__in={
                    row["awarded_by"]
                    for row in earned_map.values()
                    if row["awarded_by"] and row["awarded_by"] != "system"
                }
            )
        }
        badges = Badge.objects.filter(
            course_id__in=enrolled_course_ids
        ).select_related("course")

        finished_counts = Counter(
            UserProgress.objects.filter(
                user=request.user,
                status=UserProgress.ProgressStatus.FINISH,
                module__course_id__in=enrolled_course_ids,
            ).values_list("module__course_id", flat=True)
        )
        total_counts = Counter(
            CourseModule.objects.filter(
                course_id__in=enrolled_course_ids
            ).values_list("course_id", flat=True)
        )
        payload = []
        for badge in badges:
            course_id = badge.course_id
            owner = earned_map.get(badge.pk)
            payload.append(
                {
                    "badge": BadgeSerializer(badge).data,
                    "earned": owner is not None,
                    "course": course_id,
                    "progress": {
                        "completed": finished_counts.get(course_id, 0),
                        "total": total_counts.get(course_id, 0),
                    },
                    "earned_at": (
                        serializers.DateTimeField().to_representation(
                            owner["earned_at"]
                        )
                        if owner
                        else None
                    ),
                    "awarded_by": (
                        mentor_names.get(owner["awarded_by"], owner["awarded_by"])
                        if owner
                        else ""
                    ),
                }
            )
        # Earned dulu, lalu locked (urut nama).
        payload.sort(
            key=lambda item: (not item["earned"], item["badge"]["name"])
        )
        return Response(payload)


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
        kosong yang tidak terpakai dibuang agar tidak menumpuk. Bila attempt
        sudah final dan `module.allow_retake`, attempt baru dibuat (baris
        lama tetap sebagai riwayat; skor terbaru yang dipakai leaderboard).
        """
        module = self.get_object()
        if module.module_category != CourseModule.Category.QUIZ:
            raise ValidationError({"module": ["Not a quiz module."]})
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
            raise ValidationError({"module": ["Quiz does not have any questions yet."]})

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
        elif submission.submitted_on is not None and module.allow_retake:
            # Attempt lama sudah final + retake diizinkan → attempt baru.
            # Baris lama (nilai + jawaban) tetap tersimpan untuk riwayat;
            # leaderboard memakai attempt terbaru (latest-wins).
            submission = Submission.objects.create(
                user=request.user,
                assignment=None,
                submission_url="",
                score=0,
                reviewed_by="",
            )

        final = submission.submitted_on is not None
        # Kunci jawaban dibuka setelah dinilai final (tanpa essay = "system").
        graded = bool(submission.reviewed_by)
        payload = quiz_result_payload(submission, questions, reveal=graded)
        shuffle_quiz_payload(payload, f"quiz:{submission.pk}")
        payload["completed"] = final
        if final:
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
            raise ValidationError({"module": ["Not a quiz module."]})
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
        if submission.submitted_on is not None:
            raise ValidationError(
                {"submission": ["Quiz has already been submitted."]}
            )
        module_id = derive_submission_module_id(submission)
        if module_id is not None and module_id != module.pk:
            raise ValidationError(
                {"submission": ["This submission is not for that module."]}
            )

        questions = list(
            module.question_set.prefetch_related("questionoption_set").order_by(
                "sequence", "id"
            )
        )
        if not questions:
            raise ValidationError({"module": ["Quiz does not have any questions yet."]})

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
                        "Complete all answers before submitting the quiz. "
                        f"There are still {len(missing)} unanswered questions."
                    ]
                }
            )

        weights = split_points(module, questions)
        correct = count_correct_answers(submission, questions)
        auto_score = compute_auto_score(weights, correct)
        has_essay = weights.essay_count > 0

        is_late = bool(module.due_at and timezone.now() > module.due_at)
        submission.score = auto_score
        submission.is_late = is_late
        submission.submitted_on = timezone.now()
        submission.reviewed_by = "" if has_essay else "system"
        submission.save(
            update_fields=["score", "is_late", "submitted_on", "reviewed_by"]
        )

        UserProgress.objects.update_or_create(
            module=module,
            user=request.user,
            defaults={
                "status": UserProgress.ProgressStatus.FINISH,
                "complete_at": timezone.now(),
            },
        )
        _, new_badges = sync_leaderboard(request.user, module.course)

        payload = quiz_result_payload(submission, questions, reveal=True)
        shuffle_quiz_payload(payload, f"quiz:{submission.pk}")
        payload["completed"] = True
        payload["result"] = quiz_result_summary(submission, questions, module)
        payload["earned_badges"] = BadgeSerializer(
            [entry.badge for entry in new_badges], many=True
        ).data
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
    queryset = CourseEnrollment.objects.select_related("user", "course").order_by(
        "id"
    )
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
        # Pemilik course boleh melihat peserta course miliknya (untuk
        # pemilihan student saat memberi badge manual).
        owned_course_ids = Course.objects.filter(user=user).values_list(
            "id", flat=True
        )
        return queryset.filter(Q(user=user) | Q(course_id__in=owned_course_ids))

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
    Baris bonus manual mentor (`is_manual`, module NULL) tidak dihapus dan
    poinnya dijumlahkan ke total.

    Evaluasi badge otomatis (`sync_badges`) dijalankan di akhir, sehingga
    setiap jalur mutasi poin ikut mengecek pemberian/cabutan badge.

    Returns:
        tuple: (leaderboard, list badge yang baru didapat pada panggilan ini)
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

    # Baris bonus manual mentor (module NULL + is_manual) dilindungi dari
    # delete/recompute — poinnya ikut dijumlahkan ke total.
    manual_points = sum(
        LeaderboardDetail.objects.filter(
            leaderboard=leaderboard, is_manual=True
        ).values_list("point", flat=True)
    )
    total_points += manual_points
    if leaderboard.total_points != total_points:
        leaderboard.total_points = total_points
        leaderboard.save(update_fields=["total_points"])

    LeaderboardDetail.objects.filter(leaderboard=leaderboard, module__isnull=False).exclude(
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

    new_badges = sync_badges(user, course)
    return leaderboard, new_badges


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
                        "Upload/quiz modules are completed through assignment "
                        "submission or quiz completion, not manual marking."
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
        _, new_badges = sync_leaderboard(request.user, module.course)
        data = self.get_serializer(progress).data
        data["earned_badges"] = BadgeSerializer(
            [entry.badge for entry in new_badges], many=True
        ).data
        return Response(data, status=status.HTTP_201_CREATED)

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
        (`Submission.created_at` — momen baris submission dibuat) pada hari
        yang sama (zona WIB). `days` selalu berisi 7 hari terakhir (terakhir
        = hari ini); `current_streak` boleh berawal dari kemarin bila hari ini
        belum ada aktivitas.
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
            Submission.objects.filter(user=user, created_at__gte=window_start)
            .values_list("created_at", flat=True),
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
        _, new_badges = sync_leaderboard(request.user, module.course)
        return Response(
            {
                "module_completed": True,
                "earned_badges": BadgeSerializer(
                    [entry.badge for entry in new_badges], many=True
                ).data,
            }
        )


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
                {"detail": ["Quiz already has submissions — questions cannot be deleted."]}
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

    def list(self, request, *args, **kwargs):
        """Bulk-fill `user_totals` (total poin lintas course) untuk level."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            totals = self._user_totals(page)
            serializer = self.get_serializer(
                page,
                many=True,
                context={**self.get_serializer_context(), "user_totals": totals},
            )
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(
            queryset,
            many=True,
            context={
                **self.get_serializer_context(),
                "user_totals": self._user_totals(queryset),
            },
        )
        return Response(serializer.data)

    @staticmethod
    def _user_totals(queryset):
        return dict(
            Leaderboard.objects.filter(
                user_id__in={row.user_id for row in queryset}
            )
            .values("user_id")
            .annotate(total=Sum("total_points"))
            .values_list("user_id", "total")
        )

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
            "is_manual", "module__sequence", "id"
        )
        return Response(LeaderboardDetailSerializer(rows, many=True).data)


class PointBonusViewSet(viewsets.GenericViewSet):
    """Bonus poin manual mentor ke student enrolled (`/point-bonus/`).

    Baris disimpan sebagai `LeaderboardDetail` `is_manual` + module NULL pada
    leaderboard (user, course) target; total poin + level + badge ikut
    ter-update lewat `sync_leaderboard`.

    - GET  /point-bonus/?course=  — riwayat bonus (hanya pemilik course)
    - POST /point-bonus/          — beri bonus {course, user, point, description}
    - DELETE /point-bonus/{id}/   — cabut bonus + re-sync
    """

    queryset = LeaderboardDetail.objects.filter(is_manual=True)
    serializer_class = PointBonusSerializer

    def get_queryset(self):
        queryset = (
            self.queryset.select_related("leaderboard__user", "leaderboard__course")
            .order_by("-id")
        )
        user = self.request.user
        if not user.is_superuser:
            owned_course_ids = Course.objects.filter(user=user).values_list(
                "id", flat=True
            )
            queryset = queryset.filter(leaderboard__course_id__in=owned_course_ids)
        course = self.request.query_params.get("course")
        if course:
            queryset = queryset.filter(leaderboard__course_id=course)
        target_user = self.request.query_params.get("user")
        if target_user:
            queryset = queryset.filter(leaderboard__user_id=target_user)
        return queryset

    @staticmethod
    def _payload(detail):
        leaderboard = detail.leaderboard
        student = leaderboard.user
        return {
            "id": detail.id,
            "user": student.pk,
            "user_name": (
                student.get_full_name() or student.email or student.username
            ),
            "course": leaderboard.course_id,
            "course_title": leaderboard.course.title,
            "point": detail.point,
            "description": detail.description,
            "awarded_by": detail.awarded_by,
        }

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            [self._payload(detail) for detail in page], many=True
        )
        return self.get_paginated_response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = get_object_or_404(Course, pk=serializer.validated_data["course"])
        if course.user_id != request.user.pk:
            self.permission_denied(request, message="You do not own this course.")
        student = get_object_or_404(User, pk=serializer.validated_data["user"])
        if not CourseEnrollment.objects.filter(
            user=student, course=course
        ).exists():
            raise ValidationError(
                {"user": ["Student is not enrolled in this course."]}
            )

        leaderboard, _ = Leaderboard.objects.get_or_create(
            user=student, course=course
        )
        detail = LeaderboardDetail.objects.create(
            leaderboard=leaderboard,
            module=None,
            is_manual=True,
            description=serializer.validated_data["description"],
            point=serializer.validated_data["point"],
            awarded_by=request.user.username[:50],
        )
        sync_leaderboard(student, course)
        return Response(self._payload(detail), status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        detail = self.get_object()
        leaderboard = detail.leaderboard
        if not request.user.is_superuser and leaderboard.course.user_id != request.user.pk:
            self.permission_denied(request, message="You do not own this course.")
        detail.delete()
        sync_leaderboard(leaderboard.user, leaderboard.course)
        return Response(status=status.HTTP_204_NO_CONTENT)


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


def shuffle_quiz_payload(payload, seed):
    """Acak urutan soal & opsi pada payload quiz (deterministik per seed).

    Seed = id submission supaya urutan stabil selama mengerjakan/resume dan
    berubah pada retake (submission baru). Grading tidak terpengaruh karena
    dinilai lewat id, bukan urutan.
    """
    rng = random.Random(seed)
    rng.shuffle(payload["questions"])
    for question in payload["questions"]:
        options = question.get("options")
        if options:
            rng.shuffle(options)
    return payload


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

    def create(self, request, *args, **kwargs):
        self._earned_badges = []
        response = super().create(request, *args, **kwargs)
        response.data["earned_badges"] = BadgeSerializer(
            [entry.badge for entry in self._earned_badges], many=True
        ).data
        return response

    def perform_create(self, serializer):
        assignment = serializer.validated_data["assignment"]
        module = assignment.course_module
        user = self.request.user
        self._earned_badges = []

        # Satu submission per (assignment, user): submit ulang memperbarui
        # tautan selama belum dinilai. `is_late` hanya di-snapshot saat
        # create pertama; update URL tidak mengubahnya.
        existing = Submission.objects.filter(user=user, assignment=assignment).first()
        if existing is not None and existing.reviewed_by:
            raise ValidationError(
                {
                    "assignment": [
                        "Assignment has already been graded and cannot be resubmitted."
                    ]
                }
            )
        serializer.instance = existing
        if existing is None:
            is_late = bool(module.due_at and timezone.now() > module.due_at)
            serializer.save(
                user=user,
                score=0,
                reviewed_by="",
                is_late=is_late,
                submitted_on=timezone.now(),
            )
        else:
            serializer.save(user=user, score=0, reviewed_by="")

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
            _, self._earned_badges = sync_leaderboard(user, module.course)

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
                            "When grading, only score and reviewed_by "
                            "may be changed."
                        ]
                    }
                )
            if submission.assignment_id is None:
                raise ValidationError(
                    {"detail": ["Quiz submissions are graded via grade-essay."]}
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
                {"detail": ["Only submission_url can be updated."]}
            )
        if submission.reviewed_by:
            raise ValidationError(
                {"detail": ["Submission has already been graded and cannot be changed."]}
            )
        if submission.assignment_id is None:
            raise ValidationError(
                {"detail": ["Quiz submissions cannot be edited manually."]}
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
                {"detail": ["Assignment submissions are graded via PATCH score."]}
            )

        module = submission_module(submission)
        if module is None:
            raise ValidationError(
                {"detail": ["Quiz submission does not have any answers yet."]}
            )
        if module.course.user_id != request.user.pk:
            self.permission_denied(request, message="You do not own this course.")

        items = request.data.get("answers")
        if not isinstance(items, list) or not items:
            raise ValidationError(
                {"answers": ["At least one essay answer must be graded."]}
            )

        questions = list(module.question_set.all())
        weights = split_points(module, questions)
        if weights.essay_count == 0:
            raise ValidationError(
                {"answers": ["This module does not have any essay questions."]}
            )

        answered_ids = set(
            UserAnswer.objects.filter(submission=submission).values_list(
                "question_id", flat=True
            )
        )
        if not {question.pk for question in questions}.issubset(answered_ids):
            raise ValidationError(
                {"detail": ["Quiz has not been submitted yet and cannot be graded."]}
            )
        if not UserProgress.objects.filter(
            module=module, user=submission.user
        ).exists():
            raise ValidationError(
                {"detail": ["Quiz has not been submitted yet and cannot be graded."]}
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
                    {"answers": ["Invalid grading data format."]}
                )
            answer_id = item.get("id")
            score = item.get("score")
            if answer_id not in essay_answers:
                raise ValidationError(
                    {
                        "answers": [
                            "Only essay answers belonging to this submission "
                            "can be graded."
                        ]
                    }
                )
            if answer_id in graded:
                raise ValidationError(
                    {"answers": ["Duplicate answers found in the grading data."]}
                )
            if isinstance(score, bool) or not isinstance(score, int) or score < 0:
                raise ValidationError(
                    {"answers": ["Score must be an integer greater than or equal to 0."]}
                )
            graded[answer_id] = score

        if set(graded) != set(essay_answers):
            raise ValidationError(
                {"answers": ["All essay answers must be graded."]}
            )

        auto_score = compute_auto_score(
            weights, count_correct_answers(submission, questions)
        )
        final_score = auto_score + sum(graded.values())
        if final_score > module.point:
            raise ValidationError(
                {
                    "answers": [
                        f"Total score exceeds the module's maximum points ({module.point})."
                    ]
                }
            )

        for answer_id, score in graded.items():
            UserAnswer.objects.filter(pk=answer_id).update(score=score)
        submission.score = final_score
        submission.reviewed_by = request.user.username[:50]
        submission.save(update_fields=["score", "reviewed_by"])
        new_badges = []
        if CourseEnrollment.objects.filter(
            user=submission.user, course=module.course
        ).exists():
            _, new_badges = sync_leaderboard(submission.user, module.course)
        data = SubmissionSerializer(submission).data
        data["earned_badges"] = BadgeSerializer(
            [entry.badge for entry in new_badges], many=True
        ).data
        return Response(data)


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
            submission = existing.submission if existing else Submission.objects.filter(
                pk=submission_id, user=self.request.user
            ).first()
            if submission is not None and (
                submission.submitted_on is not None or submission.reviewed_by
            ):
                raise ValidationError(
                    {"detail": ["Quiz has already been submitted and answers cannot be changed."]}
                )
        serializer = self.get_serializer(data=request.data, instance=existing)
        serializer.is_valid(raise_exception=True)
        answer = serializer.save()
        return Response(
            self.get_serializer(answer).data, status=status.HTTP_201_CREATED
        )

    def perform_destroy(self, instance):
        if instance.submission.user_id != self.request.user.pk:
            self.permission_denied(self.request, message="Not allowed.")
        if instance.submission.submitted_on is not None or instance.submission.reviewed_by:
            raise ValidationError(
                {"detail": ["Quiz has already been submitted and answers cannot be deleted."]}
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
