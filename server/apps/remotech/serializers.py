from pathlib import Path

from rest_framework import serializers

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


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"
        read_only_fields = ["user", "slug"]

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


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseEnrollment
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
