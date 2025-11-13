from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


# =========================================================
# CUSTOM USER MODEL
# =========================================================
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


# =========================================================
# SKILL
# =========================================================
class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# =========================================================
# CERTIFICATION
# =========================================================
class Certification(models.Model):
    name = models.CharField(max_length=150)
    issuer = models.CharField(max_length=150, blank=True)
    issued_at = models.DateField(null=True, blank=True)
    level = models.CharField(max_length=50, blank=True)
    skills = models.ManyToManyField("Skill", blank=True, related_name="certifications")

    def __str__(self):
        return self.name


# =========================================================
# UNIVERSITY
# =========================================================
class University(models.Model):
    name = models.CharField(max_length=200, unique=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    email_domain = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


# =========================================================
# PROFILE
# =========================================================
class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('recruiter', 'Recruiter'),
        ('university', 'University'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField("api.User", on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    field_of_study = models.CharField(max_length=150, blank=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    score = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    skills = models.ManyToManyField(Skill, blank=True, related_name='profiles')
    certifications = models.ManyToManyField(Certification, blank=True, related_name='profiles')
    company = models.ForeignKey("api.Company", on_delete=models.SET_NULL, null=True, blank=True,related_name='employees')
    def __str__(self):
        return f"{self.user.email} ({self.role})"

# =========================================================
# COMPANY
# =========================================================
class Company(models.Model):
    name = models.CharField(max_length=200, unique=True)
    industry = models.CharField(max_length=150, blank=True)
    website = models.URLField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name
# =========================================================
# OFFER
# =========================================================
class Offer(models.Model):
    LEVEL_CHOICES = [
        ('intern', 'Internship'),
        ('junior', 'Junior'),
        ('senior', 'Senior')
    ]

    title = models.CharField(max_length=200)
    company = models.ForeignKey("api.Company", on_delete=models.CASCADE, related_name="offers", db_column="company_id")
    description = models.TextField(blank=True)
    field_required = models.CharField(max_length=150, blank=True)
    level_required = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='intern')
    required_skills = models.ManyToManyField("api.Skill", blank=True, related_name='offers')
    location = models.CharField(max_length=150, blank=True)
    deadline = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    extended_deadline = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey("api.User", on_delete=models.SET_NULL, null=True, related_name="offers_created")
    verified_by_university = models.ForeignKey("api.University", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} @ {self.company.name}"


# =========================================================
# APPLICATION
# =========================================================
class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ]

    user = models.ForeignKey("api.User", on_delete=models.CASCADE, related_name="applications")
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    predicted_fit = models.FloatField(null=True, blank=True)
    final_rank = models.IntegerField(null=True, blank=True)
    is_fake = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "offer")
        indexes = [models.Index(fields=["user", "offer"])]

    def __str__(self):
        return f"{self.user.email} -> {self.offer.title}"


# =========================================================
# FEEDBACK
# =========================================================
class Feedback(models.Model):
    FEEDBACK_TYPE_CHOICES = [
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ]

    application = models.ForeignKey("api.Application", on_delete=models.CASCADE, related_name="feedbacks")
    recruiter = models.ForeignKey("api.User", on_delete=models.SET_NULL, null=True, related_name="given_feedbacks")
    feedback_type = models.CharField(max_length=10, choices=FEEDBACK_TYPE_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback ({self.feedback_type}) on {self.application}"


# =========================================================
# SCORE HISTORY
# =========================================================
class ScoreHistory(models.Model):
    user = models.ForeignKey("api.User", on_delete=models.CASCADE, related_name="score_events")
    reason = models.CharField(max_length=200)
    points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} +{self.points} ({self.reason})"
