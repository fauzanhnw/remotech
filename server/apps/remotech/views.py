from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from server.apps.remotech.models import (
    Assignment,
    Course,
    CourseEnrollment,
    CourseModule,
    Leaderboard,
    ModuleCategory,
    Submission,
)
from server.apps.remotech.serializers import (
    AssignmentSerializer,
    CourseSerializer,
    LeaderboardSerializer,
    ModuleCategorySerializer,
    SubmissionSerializer,
)


class ModuleCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModuleCategory.objects.all()
    serializer_class = ModuleCategorySerializer


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer


class LeaderboardViewSet(viewsets.ModelViewSet):
    queryset = Leaderboard.objects.all()
    serializer_class = LeaderboardSerializer


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
