from pathlib import Path

from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.utils.html import is_html_input

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
    User,
    UserAnswer,
    UserBadge,
)
from server.apps.remotech.services.auth import MENTOR_GROUP
from server.apps.remotech.services.course import convert_to_webp
from server.apps.remotech.services.module_content import validate_module_content
from server.apps.remotech.services.richtext import (
    absolutize_media_url,
    absolutize_media_urls,
)

MAX_DOCUMENT_SIZE = 20 * 1024 * 1024
DOCUMENT_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "csv",
    "zip",
}


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = "__all__"


class UserBadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBadge
        fields = "__all__"


class UserAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAnswer
        fields = "__all__"


class MissingAsEmptyBooleanField(serializers.BooleanField):
    """Boolean field that treats a key absent from form input as unset.

    DRF's BooleanField returns False for absent keys in HTML-form data
    (multipart/urlencoded QueryDict), which would silently override the
    model default on create and reset booleans on update. Treating the
    missing key as `empty` keeps form input consistent with JSON input.
    """

    def get_value(self, dictionary):
        if is_html_input(dictionary) and self.field_name not in dictionary:
            return empty
        return super().get_value(dictionary)


class CourseSerializer(serializers.ModelSerializer):
    is_publish = MissingAsEmptyBooleanField(required=False)
    is_open = MissingAsEmptyBooleanField(required=False)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = "__all__"
        read_only_fields = ["user", "slug"]

    def get_user_name(self, obj):
        if obj.user_id is None:
            return ""
        return obj.user.get_full_name() or obj.user.username

    def validate_thumbnail(self, value):
        if not value:
            return value
        return convert_to_webp(value)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        thumbnail = result.get("thumbnail")
        if thumbnail:
            result["thumbnail"] = absolutize_media_url(thumbnail)
        return result


class CourseModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseModule
        fields = "__all__"


class ModuleContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleContent
        fields = "__all__"

    def validate(self, attrs):
        return validate_module_content(attrs, instance=self.instance)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["content_text"] = absolutize_media_urls(result.get("content_text") or "")
        return result


class ImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def validate_image(self, value):
        return convert_to_webp(value, label="Image")


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if value.size > MAX_DOCUMENT_SIZE:
            raise serializers.ValidationError("Document must be 20 MB or smaller.")

        extension = Path(value.name).suffix.lower().lstrip(".")
        if extension not in DOCUMENT_EXTENSIONS:
            allowed = ", ".join(sorted(DOCUMENT_EXTENSIONS))
            raise serializers.ValidationError(
                f"Unsupported document type. Allowed types: {allowed}."
            )

        return value

    def validate(self, attrs):
        attrs["extension"] = Path(attrs["file"].name).suffix.lower().lstrip(".")
        return attrs


class CourseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOrder
        fields = "__all__"
        read_only_fields = [
            "user",
            "order_no",
            "transaction_status",
            "gross_amount",
            "payment_type",
            "midtrans_transaction_id",
            "snap_token",
            "created_at",
            "paid_at",
        ]


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseEnrollment
        fields = "__all__"


class EnrollCourseSerializer(serializers.Serializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())


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


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value


class SetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class CurrentUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    is_mentor = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "is_mentor"]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_is_mentor(self, obj):
        return obj.groups.filter(name=MENTOR_GROUP).exists()
