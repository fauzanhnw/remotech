from django.contrib.auth.models import User
from django.shortcuts import render
from django_filters.rest_framework import (
    DjangoFilterBackend,
    OrderingFilter,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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
    LeaderboardSerializer,
    SubmissionSerializer,
    UserAnswerSerializer,
    UserBadgeSerializer,
)


class BadgeViewSet(viewsets.ModelViewSet):
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    filter_backends = DjangoFilterBackend


class UserBadgeViewSet(viewsets.ModelViewSet):
    queryset = UserBadge.objects.all()
    serializer_class = UserBadgeSerializer
    filter_backends = DjangoFilterBackend


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    filter_backends = DjangoFilterBackend


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
