import pandas as pd
from api.models import Application

def export_dataset():
    data = []

    # Get all applications, with related user and offer data
    applications = Application.objects.select_related("user", "offer")

    for app in applications:
        user = app.user
        profile = user.profile
        offer = app.offer

        # count overlapping skills between student and offer
        skill_overlap = profile.skills.filter(id__in=offer.required_skills.all()).count()
        total_skills = profile.skills.count() or 1  # avoid zero division
        skill_match_ratio = skill_overlap / total_skills

        data.append({
            "user_id": user.id,
            "username": user.username,
            "offer_id": offer.id,
            "offer_title": offer.title,
            "gpa": float(profile.gpa or 0),
            "score": profile.score,
            "field_of_study": profile.field_of_study,
            "field_required": offer.field_required,
            "skill_match_ratio": round(skill_match_ratio, 2),
            "status": 1 if app.status == "accepted" else 0
        })

    df = pd.DataFrame(data)
    df.to_csv("training_dataset.csv", index=False)
    print(f"✅ Exported {len(df)} rows to training_dataset.csv")

    return df
