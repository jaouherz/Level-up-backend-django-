from django.contrib.auth.models import User
from api.models import Offer, Application
from api.ml_utils import predict_fit

def simulate_all_applications():
    offers = Offer.objects.all()
    users = User.objects.exclude(username__iexact="admin")  # skip admin

    for offer in offers:
        for user in users:
            profile = getattr(user, "profile", None)
            if not profile:
                continue

            # Create or update application
            app, _ = Application.objects.get_or_create(user=user, offer=offer)
            prob = predict_fit(profile, offer)
            app.predicted_fit = prob
            app.save()
            print(f"✅ {user.username} -> {offer.title} = {prob:.3f}")

    print("\n🎯 Simulation complete!")
