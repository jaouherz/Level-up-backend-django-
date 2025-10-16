from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import User

from .ml_utils import predict_fit
from .models import Profile, Application


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """Create a Profile automatically when a new User is created."""
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    """Save the profile whenever the User is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()
@receiver(post_save, sender=Profile)
def update_applications_fit(sender, instance, **kwargs):
    for app in Application.objects.filter(user=instance.user):
        app.predicted_fit = predict_fit(instance, app.offer)
        app.save(update_fields=['predicted_fit'])

@receiver(m2m_changed, sender=Profile.skills.through)
def update_fit_on_skills_change(sender, instance, **kwargs):
    for app in Application.objects.filter(user=instance.user):
        app.predicted_fit = predict_fit(instance, app.offer)
        app.save(update_fields=['predicted_fit'])