from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Max
from django.utils import timezone
from django.utils.text import slugify


class CrudModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    # def save(self, *args, **kwargs) -> None:
    #     """Save CRUD Model
    #     Returns:
    #         None
    #     """
    #     if not self.pk:
    #         self.created_user = self.created_user or ""
    #     self.modified_user = self.modified_user or ""
    #     return super().save(*args, **kwargs)

    class Meta:
        abstract = True


class Course(CrudModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    slug = models.TextField()
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(
        upload_to="courses/thumbnails/", blank=True, null=True
    )
    price = models.BigIntegerField(default=0)
    is_publish = models.BooleanField(default=False)
    is_open = models.BooleanField(default=True)

    def save(self, **kwargs):
        self.slug = slugify(self.title)
        if (
            update_fields := kwargs.get("update_fields")
        ) is not None and "title" in update_fields:
            kwargs["update_fields"] = {"slug"}.union(update_fields)

        old_thumbnail = None
        if self.pk:
            old_thumbnail = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("thumbnail", flat=True)
                .first()
            )

        super().save(**kwargs)

        new_thumbnail = self.thumbnail.name or ""
        if old_thumbnail and old_thumbnail != new_thumbnail:
            self.delete_thumbnail(old_thumbnail)

    @staticmethod
    def delete_thumbnail(name):
        if name and default_storage.exists(name):
            default_storage.delete(name)

    def __str__(self):
        return self.title


class CourseEnrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "user"], name="unique_course_enrollment"
            )
        ]


class CourseOrder(models.Model):
    class StatusChoices(models.TextChoices):
        SETTLEMENT = "settlement", "Settlement"
        PENDING = "pending", "Pending"
        DENY = "deny", "Deny"
        CANCEL = "cancel", "Cancel"
        EXPIRE = "expire", "Expire"
        FAILURE = "failure", "Failure"

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_no = models.CharField(max_length=100, unique=True)
    transaction_status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True,
    )
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=30)
    midtrans_transaction_id = models.CharField(max_length=100)
    snap_token = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True)


class Badge(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)


class CourseModule(CrudModel):
    class Category(models.TextChoices):
        TEXT = "text", "Text"
        VIDEO = "video", "Video"
        UPLOAD = "upload", "Upload"
        QUIZ = "quiz", "Quiz"

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    module_category = models.CharField(
        max_length=100, choices=Category.choices, default=Category.TEXT
    )
    sequence = models.BigIntegerField(null=True, blank=True)
    point = models.IntegerField(default=100)

    def save(self, *args, **kwargs):
        if self.sequence is None:
            max_seq = CourseModule.objects.filter(course=self.course).aggregate(
                max_sequence=Max("sequence")
            )["max_sequence"]

            self.sequence = (max_seq or 0) + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.course})"


class ModuleContent(CrudModel):
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE)
    content_text = models.TextField(blank=True)
    content_url = models.URLField(blank=True)

    def __str__(self):
        return self.content_text[:50] or self.content_url or str(self.module)


class Assignment(CrudModel):
    course_module = models.ForeignKey(CourseModule, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class Submission(CrudModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    submission_url = models.URLField()
    submit_on = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField(default=0)
    reviewed_by = models.CharField(max_length=50, blank=True)


class Leaderboard(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_points = models.IntegerField(default=0)


class LeaderboardDetail(models.Model):
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE)
    description = models.CharField(max_length=255, blank=True)
    point = models.IntegerField(default=0)


class UserProgress(models.Model):
    class ProgressStatus(models.TextChoices):
        UNFINISH = "unfinish", "Unfinish"
        FINISH = "finish", "Finish"

    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    complete_at = models.DateTimeField(null=True)
    # last_access_at = models.DateTimeField(auto_now=True, auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=ProgressStatus.choices,
        default=ProgressStatus.UNFINISH,
    )


class Question(CrudModel):
    class QuestionType(models.TextChoices):
        CHOICES = "choices", "Choices"
        ESSAI = "essai", "Essai"
        BOOLEAN = "boolean", "Boolean"

    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE)
    question_text = models.TextField()
    question_type = models.CharField(max_length=50, choices=QuestionType.choices)
    explanation = models.TextField()
    sequence = models.BigIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.sequence is None:
            max_seq = CourseModule.objects.filter(course=self.module.course).aggregate(
                max_sequence=Max("sequence")
            )["max_sequence"]

            self.sequence = (max_seq or 0) + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.question_text[:50]


class QuestionOption(CrudModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    sequence = models.BigIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.sequence is None:
            max_seq = CourseModule.objects.filter(
                course=self.question.module.course
            ).aggregate(max_sequence=Max("sequence"))["max_sequence"]

            self.sequence = (max_seq or 0) + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.option_text[:50]


class UserAnswer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    question_option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE)
    answer_text = models.TextField()


class SetPasswordToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() - self.created_at > timezone.timedelta(hours=24)
