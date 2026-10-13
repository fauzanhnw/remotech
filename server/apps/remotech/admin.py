from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from server.apps.remotech.models import (
    Assignment,
    Badge,
    Course,
    CourseEnrollment,
    CourseModule,
    CourseOrder,
    Leaderboard,
    LeaderboardDetail,
    ModuleContent,
    Question,
    QuestionOption,
    Submission,
    UserBadge,
    UserProgress,
)


class ModuleContentInline(admin.TabularInline):
    model = ModuleContent
    extra = 1


class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 1


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "price", "is_publish", "is_open", "created_at")
    list_filter = ("is_publish", "is_open")
    search_fields = ("title", "description")
    ordering = ("-created_at",)


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "module_category", "sequence", "point")
    list_filter = ("module_category",)
    search_fields = ("title",)
    ordering = ("course", "sequence")
    inlines = [ModuleContentInline, AssignmentInline, QuestionInline]


@admin.register(ModuleContent)
class ModuleContentAdmin(admin.ModelAdmin):
    list_display = ("module", "content_url")
    search_fields = ("content_text", "content_url")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("name", "course_module", "created_at")
    search_fields = ("name",)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "assignment",
        "score",
        "submitted_on",
        "reviewed_by",
    )
    search_fields = ("user__username", "reviewed_by")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "module", "question_type", "sequence")
    list_filter = ("question_type",)
    search_fields = ("question_text",)
    ordering = ("module", "sequence")
    inlines = [QuestionOptionInline]


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ("question", "option_text", "is_correct", "sequence")
    list_filter = ("is_correct",)
    search_fields = ("option_text",)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "rule_type", "reward", "icon_name")
    list_filter = ("rule_type",)
    search_fields = ("name",)


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "awarded_by", "earned_at")
    search_fields = ("user__username", "badge__name", "awarded_by")
    ordering = ("-earned_at",)


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "module", "status", "complete_at")
    list_filter = ("status",)
    search_fields = ("user__username",)


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "enrolled_at")
    search_fields = ("user__username",)


@admin.register(CourseOrder)
class CourseOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_no",
        "user",
        "course",
        "transaction_status",
        "gross_amount",
        "paid_at",
    )
    list_filter = ("transaction_status",)
    search_fields = ("order_no", "user__username")


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "total_points")
    search_fields = ("user__username",)


@admin.register(LeaderboardDetail)
class LeaderboardDetailAdmin(admin.ModelAdmin):
    list_display = ("leaderboard", "module", "description", "point", "is_manual", "awarded_by")
    list_filter = ("is_manual",)
    search_fields = ("description", "awarded_by", "leaderboard__user__username")


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = BaseUserAdmin.list_display + ("get_groups",)

    @admin.display(description="Groups", ordering="groups__name")
    def get_groups(self, obj):
        return ", ".join(group.name for group in obj.groups.all())
