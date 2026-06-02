from rest_framework import serializers

from server.apps.remotech.models import (
    Assignment,
    Course,
    CourseEnrollment,
    CourseModule,
    Leaderboard,
    ModuleCategory,
    Submission,
)


class ModuleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleCategory
        fields = "_all_"


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"


class LeaderboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leaderboard
        fields = "__all__"


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = "__all__"
