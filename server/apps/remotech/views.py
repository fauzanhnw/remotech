from django.contrib.auth.models import User
from django.shortcuts import render
from django_filters.rest_framework import (
    DjangoFilterBackend,
    OrderingFilter,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from server.apps.remotech.mixins import AssignUserMixin
from server.apps.remotech.models import (
    Assignment,
    Badge,
    Course,
    CourseEnrollment,
    CourseModule,
    CourseOrder,
    Leaderboard,
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
    ForgotPasswordSerializer,
    LeaderboardSerializer,
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


class UserViewSet(viewsets.ViewSet):
    pass


class BadgeViewSet(viewsets.ModelViewSet):
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    filter_backends = DjangoFilterBackend


class UserBadgeViewSet(viewsets.ModelViewSet):
    queryset = UserBadge.objects.all()
    serializer_class = UserBadgeSerializer
    filter_backends = DjangoFilterBackend


class CourseViewSet(AssignUserMixin, viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    # filter_backends = DjangoFilterBackend

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated()]


class CourseModuleViewSet(viewsets.ModelViewSet):
    queryset = CourseModule.objects.all()
    serializer_class = CourseModuleSerializer
    filter_backends = DjangoFilterBackend


class CourseOrderViewSet(viewsets.ModelViewSet):
    queryset = CourseOrder.objects.all()
    serializer_class = CourseOrderSerializer
    filter_backends = DjangoFilterBackend


class CourseEnrollmentViewSet(viewsets.ModelViewSet):
    queryset = CourseEnrollment.objects.all()
    serializer_class = CourseEnrollmentSerializer
    filter_backends = DjangoFilterBackend


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    filter_backends = DjangoFilterBackend


class LeaderboardViewSet(viewsets.ModelViewSet):
    queryset = Leaderboard.objects.all()
    serializer_class = LeaderboardSerializer
    filter_backends = DjangoFilterBackend


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    filter_backends = DjangoFilterBackend


class UserAnswerViewSet(viewsets.ModelViewSet):
    queryset = UserAnswer.objects.all()
    serializer_class = UserAnswerSerializer
    filter_backends = DjangoFilterBackend


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

    def create(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_password(**serializer.validated_data)
        return Response(
            {"message": "Password set successfully. You can now login."},
            status=status.HTTP_200_OK,
        )


class SetPasswordPageView(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        return render(request, "set_password.html")


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
        reset_password(**serializer.validated_data)
        return Response(
            {"message": "Password reset successfully. You can now login."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordPageView(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        return render(request, "reset_password.html")
