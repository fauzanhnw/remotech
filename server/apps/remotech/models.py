from django.db import models

class CrudModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    created_user = models.CharField(max_length=50, blank=True, default="")
    modified_user = models.CharField(max_length=50, blank=True, default="")
    objects = models.BaseManager.from_queryset(CrudModelQuerySet)()

    def save(self, *args, **kwargs) -> None:
        """Save CRUD Model
        Returns:
            None
        """
        if not self.pk:
            self.created_user = self.created_user or ""
        self.modified_user = self.modified_user or ""
        return super().save(*args, **kwargs)

    class Meta:
        abstract = True

class Status(CrudModel):
    name = models.CharField(max_length=20)
    sequence = models.BigIntegerField()
    
class ModuleCategory(CrudModel):
    name = models.CharField(max_length=50)
    
class Course(CrudModel):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.BigIntegerField()
    is_publish = models.BooleanField(default=False)
    
class CourseEnrollment(CrudModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    # user
    
class Badge(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    
class UserBagde(models.Model):
    # user
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_on = models.DateTimeField(auto_now=True, auto_now_add=True)
    
class CourseModule(CrudModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    module_category = models.ForeignKey(ModuleCategory, on_delete=models.CASCADE)
    sequence = models.BigIntegerField()
    point = models.IntegerField()
    
class ModuleContent(CrudModel):
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE)
    content_text = models.TextField()
    content_url = models.URLField()
    
class Assignment(CrudModel):
    course_module = models.ForeignKey(CourseModule, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()

class Submission(CrudModel):
    # user 
    score = models.IntegerChoices
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    submission_url = models.URLField()
    submit_on = models.DateTimeField(auto_now=True, auto_now_add=True)
    
class Leaderboard(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    # user 
    points = models.IntegerField()
    
class UserProgress(models.Model):
    PROGRESS_STATUS = [
        {"UNFINISH", "Unfinish"},
        {"FINISH", "Finish"}
    ]
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE)
    # user 
    complete_at = models.DateTimeField(auto_now=True, auto_now_add=True)
    last_access_at = models.DateTimeField()
    status = models.TextChoices(choices=PROGRESS_STATUS,)
    
class PaymentTransaction(CrudModel):
    # user 
    course = models.ForeignKey(CourseModule, on_delete=models.CASCADE)
    amount = models.IntegerField()
    transaction_no = models.CharField() # auto generate
    status = models.TextChoices()
    payment_type = models.TextChoices()