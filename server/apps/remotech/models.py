from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        user = self.create_user(email, password, **extra_fields)
        UserProfile.objects.get_or_create(user=user)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['email']

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=150, blank=True, default='')
    last_name = models.CharField(max_length=150, blank=True, default='')
    total_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    avatar_url = models.URLField(blank=True, default='')

    class Meta:
        db_table = 'user_profile'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.user.email


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_published = models.BooleanField(default=False)
    created_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='courses_created'
    )
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course'
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        ordering = ['-created_on']

    def __str__(self):
        return self.title


class CourseDetail(models.Model):
    course = models.OneToOneField(
        Course, on_delete=models.CASCADE, related_name='detail'
    )
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'course_detail'
        verbose_name = 'Course Detail'
        verbose_name_plural = 'Course Details'

    def __str__(self):
        return f'Detail for {self.course.title}'


class ModuleCategory(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'module_category'
        verbose_name = 'Module Category'
        verbose_name_plural = 'Module Categories'

    def __str__(self):
        return self.name


class Module(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='modules'
    )
    module_category = models.ForeignKey(
        ModuleCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='modules'
    )
    name = models.CharField(max_length=255)
    sequence = models.IntegerField(default=0)
    point = models.IntegerField(default=0)
    created_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='modules_created'
    )
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'module'
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'
        ordering = ['sequence']

    def __str__(self):
        return f'{self.course.title} - {self.name}'


class ModuleContent(models.Model):
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name='contents'
    )
    content_text = models.TextField(blank=True, default='')
    content_url = models.URLField(blank=True, default='')

    class Meta:
        db_table = 'module_content'
        verbose_name = 'Module Content'
        verbose_name_plural = 'Module Contents'

    def __str__(self):
        return f'Content for {self.module.name}'


class Assignment(models.Model):
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name='assignments'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    deadline = models.DateTimeField(null=True, blank=True)
    max_score = models.IntegerField(default=100)

    class Meta:
        db_table = 'assignment'
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'

    def __str__(self):
        return f'{self.module.name} - {self.name}'


class Submission(models.Model):
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name='submissions'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='submissions'
    )
    submission_url = models.URLField()
    submit_on = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'submission'
        verbose_name = 'Submission'
        verbose_name_plural = 'Submissions'
        unique_together = ['assignment', 'user']

    def __str__(self):
        return f'{self.user.email} - {self.assignment.name}'


class UserProgress(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='progress'
    )
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name='progress'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='in_progress'
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    last_access_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_progress'
        verbose_name = 'User Progress'
        verbose_name_plural = 'User Progresses'
        unique_together = ['user', 'module']

    def __str__(self):
        return f'{self.user.email} - {self.module.name} - {self.status}'


class CourseEnrollment(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='enrollments'
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='enrollments'
    )
    enroll_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_enrollment'
        verbose_name = 'Course Enrollment'
        verbose_name_plural = 'Course Enrollments'
        unique_together = ['user', 'course']

    def __str__(self):
        return f'{self.user.email} -> {self.course.title}'


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='payments'
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='payments'
    )
    transaction_no = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_transaction'
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'

    def __str__(self):
        return f'{self.transaction_no} - {self.status}'


class Badge(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='badges'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon_url = models.URLField(blank=True, default='')

    class Meta:
        db_table = 'badge'
        verbose_name = 'Badge'
        verbose_name_plural = 'Badges'

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='badges'
    )
    badge = models.ForeignKey(
        Badge, on_delete=models.CASCADE, related_name='user_badges'
    )
    earned_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_badge'
        verbose_name = 'User Badge'
        verbose_name_plural = 'User Badges'
        unique_together = ['user', 'badge']

    def __str__(self):
        return f'{self.user.email} - {self.badge.name}'


class Leaderboard(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='leaderboard_entries'
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='leaderboard_entries'
    )
    points = models.IntegerField(default=0)

    class Meta:
        db_table = 'leaderboard'
        verbose_name = 'Leaderboard'
        verbose_name_plural = 'Leaderboards'
        unique_together = ['user', 'course']
        ordering = ['-points']

    def __str__(self):
        return f'{self.user.email} - {self.course.title}: {self.points} pts'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
