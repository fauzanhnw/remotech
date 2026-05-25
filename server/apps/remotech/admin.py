from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, UserProfile, Course, CourseDetail, ModuleCategory, Module,
    ModuleContent, Assignment, Submission, UserProgress,
    CourseEnrollment, PaymentTransaction, Badge, UserBadge, Leaderboard
)


class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'is_active', 'is_staff', 'is_superuser', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'groups']
    search_fields = ['email']
    ordering = ['email']
    fieldsets = [
        (None, {'fields': ['email', 'password']}),
        ('Permissions', {'fields': ['is_active', 'is_staff', 'is_superuser', 'groups']}),
        ('Important dates', {'fields': ['last_login', 'date_joined']}),
    ]
    add_fieldsets = [
        (None, {
            'classes': ['wide'],
            'fields': ['email', 'password1', 'password2'],
        }),
    ]


admin.site.register(User, UserAdmin)


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'first_name', 'last_name', 'total_points', 'level']
    search_fields = ['user__email', 'first_name', 'last_name']


admin.site.register(UserProfile, UserProfileAdmin)


class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'is_published', 'created_user', 'created_on']
    list_filter = ['is_published']
    search_fields = ['title']


admin.site.register(Course, CourseAdmin)


class CourseDetailAdmin(admin.ModelAdmin):
    list_display = ['course']


admin.site.register(CourseDetail, CourseDetailAdmin)


class ModuleCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']


admin.site.register(ModuleCategory, ModuleCategoryAdmin)


class ModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'sequence', 'point', 'created_user']
    list_filter = ['course']
    search_fields = ['name']


admin.site.register(Module, ModuleAdmin)


class ModuleContentAdmin(admin.ModelAdmin):
    list_display = ['module']


admin.site.register(ModuleContent, ModuleContentAdmin)


class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'deadline', 'max_score']
    list_filter = ['module__course']


admin.site.register(Assignment, AssignmentAdmin)


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'user', 'score', 'submit_on']
    list_filter = ['assignment__module__course']


admin.site.register(Submission, SubmissionAdmin)


class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'module', 'status', 'completed_at', 'last_access_at']
    list_filter = ['status']


admin.site.register(UserProgress, UserProgressAdmin)


class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'enroll_at']
    list_filter = ['course']


admin.site.register(CourseEnrollment, CourseEnrollmentAdmin)


class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_no', 'user', 'course', 'amount', 'status', 'created_on']
    list_filter = ['status']


admin.site.register(PaymentTransaction, PaymentTransactionAdmin)


class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'course']


admin.site.register(Badge, BadgeAdmin)


class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'earned_on']


admin.site.register(UserBadge, UserBadgeAdmin)


class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'points']
    list_filter = ['course']


admin.site.register(Leaderboard, LeaderboardAdmin)
