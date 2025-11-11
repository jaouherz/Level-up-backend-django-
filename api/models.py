from django.db import models
from django.contrib.auth.models import User


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Certification(models.Model):
    name = models.CharField(max_length=150)
    issuer = models.CharField(max_length=150, blank=True)
    issued_at = models.DateField(null=True, blank=True)
    level = models.CharField(max_length=50, blank=True)
    skills = models.ManyToManyField("Skill", blank=True, related_name="certifications")

    def __str__(self):
        return self.name

class Feedback(models.Model):
    FEEDBACK_TYPE_CHOICES = [
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ]

    application = models.ForeignKey(
        'Application',
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    recruiter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='given_feedbacks'
    )
    feedback_type = models.CharField(
        max_length=10,
        choices=FEEDBACK_TYPE_CHOICES
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback ({self.feedback_type}) on {self.application}"

class University(models.Model):
    name = models.CharField(max_length=200, unique=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    email_domain = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name



class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('recruiter', 'Recruiter'),
        ('university', 'University'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    field_of_study = models.CharField(max_length=150, blank=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    score = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    skills = models.ManyToManyField(Skill, blank=True, related_name='profiles')
    certifications = models.ManyToManyField(Certification, blank=True, related_name='profiles')

    def __str__(self):
        return f"{self.user.username} ({self.role})"



class Offer(models.Model):
    LEVEL_CHOICES = [
        ('intern', 'Internship'),
        ('junior', 'Junior'),
        ('senior', 'Senior')
    ]

    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    field_required = models.CharField(max_length=150, blank=True)
    level_required = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='intern')
    required_skills = models.ManyToManyField(Skill, blank=True, related_name='offers')
    location = models.CharField(max_length=150, blank=True)
    deadline = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    extended_deadline = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='offers')
    verified_by_university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} @ {self.company}"


class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    predicted_fit = models.FloatField(null=True, blank=True)
    final_rank = models.IntegerField(null=True, blank=True)
    is_fake = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'offer')
        indexes = [
            models.Index(fields=['user', 'offer']),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.offer.title}"



class ScoreHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='score_events')
    reason = models.CharField(max_length=200)
    points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} +{self.points} ({self.reason})"