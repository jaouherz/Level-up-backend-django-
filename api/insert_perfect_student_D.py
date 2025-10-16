from django.contrib.auth.models import User
from api.models import Offer, Profile, Application

def run():
    offer = Offer.objects.filter(title="Internship 0").first()
    if not offer:
        print("Offer not found")
        return

    print("Target offer:", offer.title)

    user, _ = User.objects.get_or_create(username="super_student")
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.role = "student"
    profile.field_of_study = offer.field_required
    profile.gpa = 4.0
    profile.score = 400
    profile.save()

    # give the same skills as the offer requires
    profile.skills.set(offer.required_skills.all())

    Application.objects.get_or_create(user=user, offer=offer)
    print(f"Student '{user.username}' added to {offer.title}")