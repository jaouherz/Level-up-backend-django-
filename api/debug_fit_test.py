from api.models import Offer, Application
from api.ml_utils import predict_fit

def run():
    offer = Offer.objects.first()
    apps = list(Application.objects.filter(offer=offer)[:10])
    for app in apps:
        fit = predict_fit(app.user.profile, offer)
        print(f"{app.user.username} | score={app.user.profile.score} | fit={fit}")

if __name__ == "__main__":
    run()