# api/gamification.py

from api.models import Application, ScoreHistory
from api.ml_utils import compute_skill_match_ratio

def update_profile_score(profile):
    """Auto compute and save profile score based on GPA, skills, certs."""
    profile.score = compute_skill_match_ratio(profile)
    profile.save(update_fields=["score"])
    return profile.score


def distribute_rank_points(offer):
    """Distribute extra gamification points to top candidates after deadline."""
    apps = (
        Application.objects
        .filter(offer=offer)
        .select_related("user__profile")
        .order_by("-predicted_fit")
    )

    if not apps.exists():
        return 0

    for i, app in enumerate(apps, start=1):
        profile = app.user.profile
        bonus = 0

        if i == 1:
            bonus = 100
        elif i == 2:
            bonus = 70
        elif i == 3:
            bonus = 50
        elif i <= 10:
            bonus = 20
        else:
            bonus = 5

        profile.score += bonus
        profile.save(update_fields=["score"])

        ScoreHistory.objects.create(
            user=app.user,
            reason=f"Rank {i} in {offer.title}",
            points=bonus
        )

    return len(apps)
