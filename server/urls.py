"""
URL configuration for server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from rest_framework.routers import DefaultRouter

from server.apps.remotech.views import (
    AssignmentViewSet,
    CourseEnrollmentViewSet,
    CourseModuleViewSet,
    CourseOrderViewSet,
    CourseViewSet,
    DocumentUploadView,
    ForgotPasswordPageView,
    ForgotPasswordResetViewSet,
    ForgotPasswordViewSet,
    ImageUploadView,
    LeaderboardViewSet,
    MidtransNotificationView,
    ModuleContentViewSet,
    RegisterViewSet,
    SetPasswordViewSet,
    SubmissionViewSet,
    TokenObtainPairViewSet,
    TokenRefreshViewSet,
    UserProgressViewSet,
    UserViewSet,
)

router = DefaultRouter()

router.register(r"course", CourseViewSet, basename="course")
router.register(r"module", CourseModuleViewSet, basename="module")
router.register(r"module-content", ModuleContentViewSet, basename="module-content")
router.register(r"order", CourseOrderViewSet, basename="order")
router.register(r"assignment", AssignmentViewSet, basename="assignment")
router.register(r"enroll", CourseEnrollmentViewSet, basename="enroll")
router.register(r"leaderboard", LeaderboardViewSet, basename="leaderboard")
router.register(r"progress", UserProgressViewSet, basename="progress")
router.register(r"submission", SubmissionViewSet, basename="submission")
router.register(r"user", UserViewSet, basename="user")

auth_router = DefaultRouter()

auth_router.register(r"register", RegisterViewSet, basename="register")
auth_router.register(r"set-password", SetPasswordViewSet, basename="set-password")
auth_router.register(
    r"forgot-password", ForgotPasswordViewSet, basename="forgot-password"
)
auth_router.register(
    r"forgot-password/reset",
    ForgotPasswordResetViewSet,
    basename="forgot-password-reset",
)
auth_router.register(r"token", TokenObtainPairViewSet, basename="token")
auth_router.register(r"token/refresh", TokenRefreshViewSet, basename="token-refresh")

urlpatterns = (
    [
        path("admin/", admin.site.urls),
        path("reset-password/", ForgotPasswordPageView.as_view({"get": "list"})),
        path("upload/image/", ImageUploadView.as_view()),
        path("upload/document/", DocumentUploadView.as_view()),
        path("payment/notification/", MidtransNotificationView.as_view()),
    ]
    + router.urls
    + auth_router.urls
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
