from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import action
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
    Leaderboard,
    ModuleContent,
    Submission,
    UserAnswer,
    UserBadge,
)
from server.apps.remotech.serializers import (
    AssignmentSerializer,
    BadgeSerializer,
    CourseEnrollmentSerializer,
    CourseModuleSerializer,
    CourseOrderSerializer,
    CourseSerializer,
    CurrentUserSerializer,
    DocumentUploadSerializer,
    EnrollCourseSerializer,
    ForgotPasswordSerializer,
    ImageUploadSerializer,
    LeaderboardSerializer,
    ModuleContentSerializer,
    RegisterSerializer,
    SetPasswordSerializer,
    SubmissionSerializer,
    UserAnswerSerializer,
    UserBadgeSerializer,
)
from server.apps.remotech.services.auth import (
    forgot_password,
    register_user,
    reset_password,
    set_password,
)
from server.apps.remotech.services.payment import (
    check_payment_status,
    enroll_course,
    handle_notification,
)
from server.apps.remotech.services.richtext import extract_media_urls


def media_url(storage_name):
    path = f"{settings.MEDIA_URL}{storage_name}"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{settings.BASE_URL.rstrip('/')}{path}"


class UserViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(CurrentUserSerializer(request.user).data)


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
    filterset_fields = ["is_open"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated()]


class CourseModuleViewSet(CourseOwnerMixin, viewsets.ModelViewSet):
    queryset = CourseModule.objects.select_related("course").order_by("id")
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


class ModuleContentViewSet(CourseOwnerMixin, viewsets.ModelViewSet):
    queryset = ModuleContent.objects.select_related(
        "module", "module__course"
    ).order_by("id")
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
    filterset_fields = ["course", "user"]

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


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.order_by("id")
    serializer_class = AssignmentSerializer
    filterset_fields = ["course_module"]


class LeaderboardViewSet(viewsets.ModelViewSet):
    queryset = Leaderboard.objects.order_by("id")
    serializer_class = LeaderboardSerializer
    filterset_fields = ["course", "user"]


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.order_by("id")
    serializer_class = SubmissionSerializer
    filterset_fields = ["assignment", "user"]


class UserAnswerViewSet(viewsets.ModelViewSet):
    queryset = UserAnswer.objects.order_by("id")
    serializer_class = UserAnswerSerializer


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
        return render(request, "set_password.html")

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
        return render(request, "reset_password.html")


class MidtransNotificationView(APIView):
    """Midtrans payment notification webhook (configured in Midtrans dashboard)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        order = handle_notification(request.data)
        return Response(CourseOrderSerializer(order).data, status=status.HTTP_200_OK)
