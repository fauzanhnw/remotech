from pathlib import Path

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
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
    LeaderboardDetail,
    ModuleContent,
    Question,
    QuestionOption,
    Submission,
    User,
    UserAnswer,
    UserBadge,
    UserProgress,
)
from server.apps.remotech.services.auth import MENTOR_GROUP
from server.apps.remotech.services.course import convert_to_webp
from server.apps.remotech.services.grading import (
    derive_submission_module_id,
    penalized_score,
    submission_module,
)
from server.apps.remotech.services.levels import level_for_points, level_progress
from server.apps.remotech.services.module_content import validate_module_content
from server.apps.remotech.services.richtext import (
    absolutize_media_url,
    absolutize_media_urls,
)

MAX_DOCUMENT_SIZE = 20 * 1024 * 1024
USERNAME_MAX_LENGTH = User._meta.get_field("username").max_length
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
    """Definisi badge per course.

    `icon_image` boleh diunggah (multipart) dan direpresentasikan sebagai
    URL absolut media; `icon_name` adalah ikon preset frontend (kosong =
    fallback trophy). `course_title` hanya untuk kenyamanan tampilan.
    """

    icon_image = serializers.ImageField(required=False, allow_null=True)
    course_title = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        field_file = getattr(instance, "icon_image", None)
        if field_file and field_file.name:
            path = f"{settings.MEDIA_URL}{field_file.name}"
            if not path.startswith("/"):
                path = f"/{path}"
            data["icon_image"] = f"{settings.BASE_URL.rstrip('/')}{path}"
        else:
            data["icon_image"] = None
        return data

    def get_course_title(self, obj):
        course = getattr(obj, "course", None)
        return getattr(course, "title", "") or ""


class UserBadgeSerializer(serializers.ModelSerializer):
    """Badge yang dimiliki user; `badge_detail` + turunan untuk tampilan."""

    badge_detail = BadgeSerializer(source="badge", read_only=True)
    course = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = UserBadge
        fields = "__all__"

    def get_course(self, obj):
        return getattr(obj.badge, "course_id", None)

    def get_course_title(self, obj):
        course = getattr(obj.badge, "course", None)
        return getattr(course, "title", "") or ""

    def get_user_name(self, obj):
        user = getattr(obj, "user", None)
        if user is None:
            return ""
        return user.get_full_name() or user.username


class UserBadgeAwardSerializer(serializers.Serializer):
    """Mentor memberi badge manual (POST /user-badge/)."""

    badge = serializers.PrimaryKeyRelatedField(queryset=Badge.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())


class UserAnswerSerializer(serializers.ModelSerializer):
    """Jawaban per soal pada submission quiz (upsert per submission+soal).

    `score` hanya boleh diisi lewat endpoint grade-essay (mentor) sehingga
    di sini read-only; soal pilihan tidak memakainya.
    """

    is_correct = serializers.SerializerMethodField()

    class Meta:
        model = UserAnswer
        fields = "__all__"
        read_only_fields = ["score"]

    def get_is_correct(self, obj):
        """Benar/salah pilihan; null untuk essay (dinilai mentor)."""
        return obj.is_correct

    def validate(self, attrs):
        request = self.context.get("request")
        submission = attrs.get("submission")
        question = attrs.get("question")
        if self.instance is not None:
            submission = submission or self.instance.submission
            question = question or self.instance.question

        if request is not None and submission.user_id != request.user.pk:
            raise serializers.ValidationError(
                {"submission": ["Hanya pemilik submission yang boleh menjawab."]}
            )
        if submission.assignment_id is not None:
            raise serializers.ValidationError(
                {"submission": ["Submission ini bukan submission quiz."]}
            )
        if submission.reviewed_by:
            raise serializers.ValidationError(
                {"submission": ["Quiz sudah disubmit dan tidak bisa dijawab lagi."]}
            )

        module_id = derive_submission_module_id(submission)
        if module_id is not None and module_id != question.module_id:
            raise serializers.ValidationError(
                {"question": ["Soal ini bukan milik module quiz tersebut."]}
            )

        option = attrs.get("question_option")
        answer_text = attrs.get("answer_text", "")
        if self.instance is not None:
            option = attrs.get("question_option", self.instance.question_option)
            answer_text = attrs.get("answer_text", self.instance.answer_text)

        if question.is_essay:
            if option is not None:
                raise serializers.ValidationError(
                    {"question_option": ["Soal essay tidak memiliki opsi pilihan."]}
                )
            if not (answer_text or "").strip():
                raise serializers.ValidationError(
                    {"answer_text": ["Jawaban essay wajib diisi."]}
                )
        else:
            if option is None:
                raise serializers.ValidationError(
                    {"question_option": ["Pilih salah satu opsi jawaban."]}
                )
            if option.question_id != question.pk:
                raise serializers.ValidationError(
                    {"question_option": ["Opsi tidak termasuk soal tersebut."]}
                )

        return attrs


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = "__all__"
        read_only_fields = ["question"]


class QuestionSerializer(serializers.ModelSerializer):
    """Soal quiz beserta opsinya (nested, tertulis/terhapus sekaligus).

    `is_correct` dan `explanation` hanya di-reveal untuk pemilik course
    (mentor) atau saat hasil quiz sudah final — mencegah student membocorkan
    kunci jawaban lewat API sebelum submit.
    """

    options = QuestionOptionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            "id",
            "module",
            "question_text",
            "question_type",
            "explanation",
            "sequence",
            "options",
            "created_at",
            "modified_at",
        ]

    def to_representation(self, instance):
        result = super().to_representation(instance)
        if not self.context.get("reveal"):
            result["explanation"] = ""
            for option in result.get("options", []):
                option.pop("is_correct", None)
        return result

    def _current(self, attrs, field):
        value = attrs.get(field)
        if value is None and self.instance is not None:
            value = getattr(self.instance, field)
        return value

    def validate(self, attrs):
        module = self._current(attrs, "module")
        if module is None:
            raise serializers.ValidationError({"module": ["This field is required."]})
        if module.module_category != CourseModule.Category.QUIZ:
            raise serializers.ValidationError(
                {"module": ["Soal hanya bisa ditambahkan ke module quiz."]}
            )

        question_type = self._current(attrs, "question_type")
        options = attrs.get("options")
        if options is None and self.instance is not None:
            options = [
                {"option_text": option.option_text, "is_correct": option.is_correct}
                for option in self.instance.questionoption_set.all()
            ]
        options = options or []

        if question_type == Question.QuestionType.ESSAI:
            if options:
                raise serializers.ValidationError(
                    {"options": ["Soal essay tidak memiliki opsi jawaban."]}
                )
        else:
            if len(options) < 2:
                raise serializers.ValidationError(
                    {"options": ["Minimal 2 opsi jawaban wajib diisi."]}
                )
            correct_count = sum(
                1 for option in options if option.get("is_correct")
            )
            if correct_count != 1:
                raise serializers.ValidationError(
                    {"options": ["Tepat satu opsi harus ditandai benar."]}
                )
            if question_type == Question.QuestionType.BOOLEAN and len(options) != 2:
                raise serializers.ValidationError(
                    {"options": ["Soal boolean harus memiliki tepat 2 opsi."]}
                )

        # Kunci jawaban dikunci begitu ada pengerjaan — menyusul poin/soal
        # akan merusak skor submission yang sudah ada.
        if self.instance is not None and UserAnswer.objects.filter(
            question__module=module
        ).exists():
            raise serializers.ValidationError(
                {"module": ["Quiz sudah ada pengerjaan — soal tidak bisa diubah."]}
            )

        return attrs

    def create(self, validated_data):
        options_data = validated_data.pop("options", [])
        question = Question.objects.create(**validated_data)
        for option in options_data:
            QuestionOption.objects.create(question=question, **option)
        return question

    def update(self, instance, validated_data):
        options_data = validated_data.pop("options", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if options_data is not None:
            instance.questionoption_set.all().delete()
            for option in options_data:
                QuestionOption.objects.create(question=instance, **option)
        return instance


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
    """Order pembelian course.

    `course_title` diturunkan dari relasi `course` (viewset sudah
    `select_related("course")`, jadi tidak ada query tambahan).
    """

    course_title = serializers.SerializerMethodField()

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

    def get_course_title(self, obj):
        course = getattr(obj, "course", None)
        return getattr(course, "title", "") or ""


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseEnrollment
        fields = "__all__"

    def get_user_name(self, obj):
        user = getattr(obj, "user", None)
        if user is None:
            return ""
        return user.get_full_name() or user.username


class EnrollCourseSerializer(serializers.Serializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())


class UserProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProgress
        fields = "__all__"
        read_only_fields = ["user", "status", "complete_at"]


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"


class LeaderboardSerializer(serializers.ModelSerializer):
    """Papan skor per course; `course_title`/`user_name` turunan relasi.

    `level`/`level_title` dihitung dari total poin peserta lintas course
    (dibulk-fill lewat context `user_totals` oleh viewset; fallback ke
    poin course ini bila konteks absen).
    """

    course_title = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    level_title = serializers.SerializerMethodField()

    class Meta:
        model = Leaderboard
        fields = "__all__"

    def _level(self, obj):
        totals = self.context.get("user_totals") or {}
        total = totals.get(obj.user_id, obj.total_points)
        return level_for_points(total)

    def get_level(self, obj):
        return self._level(obj)[0]

    def get_level_title(self, obj):
        return self._level(obj)[1]

    def get_course_title(self, obj):
        course = getattr(obj, "course", None)
        return getattr(course, "title", "") or ""

    def get_user_name(self, obj):
        user = getattr(obj, "user", None)
        if user is None:
            return ""
        return user.get_full_name() or user.username


class LeaderboardDetailSerializer(serializers.ModelSerializer):
    """Rincian poin satu baris leaderboard per module (GET /leaderboard/{id}/details/).

    `description` diisi judul module saat `sync_leaderboard`, jadi tidak perlu
    join ulang ke module untuk menampilkan teksnya. Baris bonus manual mentor
    (`is_manual`, module NULL) memakai `description` sebagai alasan bonus.
    """

    class Meta:
        model = LeaderboardDetail
        fields = ["id", "module", "description", "point", "is_manual", "awarded_by"]


class PointBonusSerializer(serializers.Serializer):
    """Bonus poin manual mentor ke student enrolled (POST/GET /point-bonus/).

    Baris disimpan sebagai `LeaderboardDetail` `is_manual` + module NULL pada
    leaderboard (user, course) target; `user`/`course` di sini adalah PK —
    bukan kolom database (diturunkan dari relasi leaderboard).
    """

    id = serializers.IntegerField(read_only=True)
    user = serializers.IntegerField()
    user_name = serializers.CharField(read_only=True)
    course = serializers.IntegerField()
    course_title = serializers.CharField(read_only=True)
    point = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255)
    awarded_by = serializers.CharField(read_only=True)


class MyLeaderboardCourseSerializer(serializers.Serializer):
    """Satu course pada ringkasan poin milik sendiri (GET /leaderboard/me/)."""

    course = serializers.IntegerField()
    course_title = serializers.CharField()
    total_points = serializers.IntegerField()
    # Null bila belum ada baris leaderboard (belum pernah menyelesaikan module).
    rank = serializers.IntegerField(allow_null=True)
    participants = serializers.IntegerField()


class MyLeaderboardSerializer(serializers.Serializer):
    """Ringkasan poin milik sendiri lintas course (GET /leaderboard/me/)."""

    total_points = serializers.IntegerField()
    # Level on-the-fly dari total_points (lihat services.levels).
    level = serializers.SerializerMethodField()
    level_title = serializers.SerializerMethodField()
    # Progres menuju level berikutnya (untuk progress bar UI).
    next_level_title = serializers.SerializerMethodField()
    points_to_next_level = serializers.SerializerMethodField()
    level_progress = serializers.SerializerMethodField()
    courses = MyLeaderboardCourseSerializer(many=True)

    def _level_data(self, obj):
        return level_progress(obj["total_points"])

    def get_level(self, obj):
        return self._level_data(obj)[0]

    def get_level_title(self, obj):
        return self._level_data(obj)[1]

    def get_next_level_title(self, obj):
        return self._level_data(obj)[2]

    def get_points_to_next_level(self, obj):
        return self._level_data(obj)[3]

    def get_level_progress(self, obj):
        return self._level_data(obj)[4]


class SubmissionSerializer(serializers.ModelSerializer):
    """Submission tugas (assignment + tautan) atau hasil quiz (tanpa assignment).

    Module untuk submission quiz diturunkan lewat jawaban (lihat
    `services.grading`), sehingga `module`/`module_title`/`max_score`/
    `course`/`course_title` di sini adalah field turunan — bukan kolom
    database.
    """

    module = serializers.SerializerMethodField()
    module_title = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    max_score = serializers.SerializerMethodField()
    is_quiz = serializers.SerializerMethodField()
    is_graded = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    # Penalti keterlambatan (soft): skor mentah `score` tetap; poin
    # leaderboard memakai `effective_score` (lihat services.grading).
    effective_score = serializers.SerializerMethodField()
    late_penalty_percent = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = "__all__"
        # user diisi backend dari request; score/reviewed_by untuk mentor (PATCH),
        # di-reset saat create oleh viewset; is_late & submitted_on di-snapshot
        # backend (upload: saat create; quiz: saat quiz/submit).
        read_only_fields = ["user", "is_late", "submitted_on"]

    def _module_id(self, obj):
        if obj.assignment_id is not None:
            return obj.assignment.course_module_id
        derived = getattr(obj, "derived_module", None)
        if derived is not None:
            return derived
        return derive_submission_module_id(obj)

    def get_module(self, obj):
        return self._module_id(obj)

    def get_module_title(self, obj):
        if obj.assignment_id is not None:
            return obj.assignment.course_module.title
        derived = getattr(obj, "derived_module_title", None)
        if derived is not None:
            return derived
        module_id = derive_submission_module_id(obj)
        if module_id is None:
            return ""
        module = CourseModule.objects.filter(pk=module_id).first()
        return module.title if module else ""

    def get_course(self, obj):
        if obj.assignment_id is not None:
            return obj.assignment.course_module.course_id
        derived = getattr(obj, "derived_course", None)
        if derived is not None:
            return derived
        module_id = self._module_id(obj)
        if module_id is None:
            return None
        return (
            CourseModule.objects.filter(pk=module_id)
            .values_list("course_id", flat=True)
            .first()
        )

    def get_course_title(self, obj):
        if obj.assignment_id is not None:
            return obj.assignment.course_module.course.title
        derived = getattr(obj, "derived_course_title", None)
        if derived is not None:
            return derived
        module_id = self._module_id(obj)
        if module_id is None:
            return ""
        module = (
            CourseModule.objects.filter(pk=module_id).select_related("course").first()
        )
        return module.course.title if module else ""

    def get_max_score(self, obj):
        if obj.assignment_id is not None:
            return obj.assignment.course_module.point
        derived = getattr(obj, "derived_module_point", None)
        if derived is not None:
            return derived
        module_id = derive_submission_module_id(obj)
        if module_id is None:
            return None
        module = CourseModule.objects.filter(pk=module_id).first()
        return module.point if module else None

    def get_is_quiz(self, obj):
        return obj.assignment_id is None

    def get_is_graded(self, obj):
        return bool(obj.reviewed_by)

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def _late_module(self, obj):
        """Module pemilik submission untuk keperluan penalti keterlambatan."""
        if obj.assignment_id is not None:
            return obj.assignment.course_module
        module_id = derive_submission_module_id(obj)
        if module_id is None:
            return None
        return CourseModule.objects.filter(pk=module_id).first()

    def get_effective_score(self, obj):
        module = self._late_module(obj)
        return penalized_score(
            obj.score,
            obj.is_late,
            module.late_penalty_percent if module is not None else 0,
        )

    def get_late_penalty_percent(self, obj):
        module = self._late_module(obj)
        return module.late_penalty_percent if module is not None else None

    def validate_score(self, value):
        if value < 0:
            raise serializers.ValidationError("Nilai tidak boleh negatif.")
        if self.instance is not None:
            module = submission_module(self.instance)
            if module is not None and value > module.point:
                raise serializers.ValidationError(
                    f"Nilai tidak boleh melebihi poin maksimal module ({module.point})."
                )
        return value

    def validate(self, attrs):
        if self.instance is None:
            assignment = attrs.get("assignment")
            if assignment is None:
                raise serializers.ValidationError(
                    {"assignment": ["This field is required."]}
                )
            if assignment.course_module.module_category != CourseModule.Category.UPLOAD:
                raise serializers.ValidationError(
                    {
                        "assignment": [
                            "Pengumpulan tugas hanya untuk module berkategori upload."
                        ]
                    }
                )
            if not attrs.get("submission_url"):
                raise serializers.ValidationError(
                    {"submission_url": ["This field is required."]}
                )
        elif "submission_url" in attrs and not attrs["submission_url"]:
            raise serializers.ValidationError(
                {"submission_url": ["This field is required."]}
            )
        return attrs


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


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Update profil milik sendiri (PATCH /user/me/).

    `username` diisi email saat registrasi dan dipakai sebagai identitas login,
    jadi saat email berganti `username` ikut diganti agar user tetap bisa
    login memakai email barunya.
    """

    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def validate_email(self, value):
        user = self.instance
        if user is None:
            return value

        taken = (
            User.objects.filter(username=value).exclude(pk=user.pk).exists()
            or User.objects.filter(email=value).exclude(pk=user.pk).exists()
        )
        if taken:
            raise serializers.ValidationError("Email already registered.")

        if user.username == user.email and len(value) > USERNAME_MAX_LENGTH:
            raise serializers.ValidationError("Email is too long to be a username.")
        return value

    def update(self, instance, validated_data):
        email = validated_data.get("email")
        if email and email != instance.email and instance.username == instance.email:
            instance.username = email
        return super().update(instance, validated_data)


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


class ChangePasswordSerializer(serializers.Serializer):
    """Ganti password user login (POST /user/change-password/).

    Wajib menyertakan password lama; password baru divalidasi memakai
    `AUTH_PASSWORD_VALIDATORS` (minimal 8 karakter, bukan password umum, dll).
    """

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        user = self.context["request"].user
        try:
            validate_password(value, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return value

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        if data["new_password"] == data["old_password"]:
            raise serializers.ValidationError(
                {
                    "new_password": (
                        "New password must be different from the current one."
                    )
                }
            )
        return data
