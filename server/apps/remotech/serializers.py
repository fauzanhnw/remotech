from rest_framework import serializers
from .models import (
    User, UserProfile, Course, CourseDetail, ModuleCategory, Module,
    ModuleContent, Assignment, Submission, UserProgress,
    CourseEnrollment, PaymentTransaction, Badge, UserBadge, Leaderboard
)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'first_name', 'last_name', 'total_points', 'level', 'avatar_url']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'is_active', 'is_staff', 'is_superuser',
                  'date_joined', 'profile', 'role']
        read_only_fields = ['is_staff', 'is_superuser', 'date_joined']

    def get_role(self, obj):
        groups = obj.groups.all()
        if groups:
            return groups[0].name
        if obj.is_superuser:
            return 'Admin'
        return 'Peserta'


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, default='')
    last_name = serializers.CharField(required=False, default='')

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']

    def create(self, validated_data):
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        UserProfile.objects.create(
            user=user, first_name=first_name, last_name=last_name
        )
        return user


class CourseDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseDetail
        fields = ['id', 'description']


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'course', 'module_category', 'name', 'sequence',
                  'point', 'created_user', 'created_on']
        read_only_fields = ['created_user', 'created_on']


class ModuleContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleContent
        fields = ['id', 'module', 'content_text', 'content_url']


class ModuleWithContentSerializer(serializers.ModelSerializer):
    contents = ModuleContentSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'course', 'module_category', 'name', 'sequence',
                  'point', 'contents']


class CourseListSerializer(serializers.ModelSerializer):
    mentor_name = serializers.SerializerMethodField()
    module_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'price', 'is_published',
                  'mentor_name', 'module_count', 'created_on']

    def get_mentor_name(self, obj):
        profile = getattr(obj.created_user, 'profile', None)
        if profile:
            return f'{profile.first_name} {profile.last_name}'.strip() or obj.created_user.email
        return obj.created_user.email

    def get_module_count(self, obj):
        return obj.modules.count()


class CourseDetailFullSerializer(serializers.ModelSerializer):
    detail = CourseDetailSerializer(read_only=True)
    modules = ModuleWithContentSerializer(many=True, read_only=True)
    mentor_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'price', 'is_published',
                  'mentor_name', 'detail', 'modules', 'created_on']

    def get_mentor_name(self, obj):
        profile = getattr(obj.created_user, 'profile', None)
        if profile:
            return f'{profile.first_name} {profile.last_name}'.strip() or obj.created_user.email
        return obj.created_user.email


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['id', 'module', 'name', 'description', 'deadline', 'max_score']


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ['id', 'assignment', 'user', 'submission_url', 'submit_on',
                  'score', 'feedback']
        read_only_fields = ['user', 'submit_on', 'score', 'feedback']


class SubmissionGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ['score', 'feedback']


class UserProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProgress
        fields = ['id', 'user', 'module', 'status', 'completed_at', 'last_access_at']
        read_only_fields = ['user', 'completed_at', 'last_access_at']


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = ['id', 'user', 'course', 'course_title', 'enroll_at']
        read_only_fields = ['user', 'enroll_at']


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ['id', 'user', 'course', 'transaction_no', 'amount',
                  'payment_type', 'status', 'created_on', 'updated_on']
        read_only_fields = ['user', 'created_on', 'updated_on']


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ['id', 'course', 'name', 'description', 'icon_url']


class UserBadgeSerializer(serializers.ModelSerializer):
    badge_name = serializers.CharField(source='badge.name', read_only=True)

    class Meta:
        model = UserBadge
        fields = ['id', 'user', 'badge', 'badge_name', 'earned_on']
        read_only_fields = ['user', 'earned_on']


class LeaderboardSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Leaderboard
        fields = ['id', 'user', 'user_email', 'user_name', 'course', 'points']

    def get_user_name(self, obj):
        profile = getattr(obj.user, 'profile', None)
        if profile:
            return f'{profile.first_name} {profile.last_name}'.strip() or obj.user.email
        return obj.user.email


class DashboardSerializer(serializers.Serializer):
    total_points = serializers.IntegerField()
    level = serializers.IntegerField()
    enrolled_courses = serializers.IntegerField()
    completed_modules = serializers.IntegerField()
    badges = UserBadgeSerializer(many=True)
    recent_activity = UserProgressSerializer(many=True)
