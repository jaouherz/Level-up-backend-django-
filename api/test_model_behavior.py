import joblib
import numpy as np
from django.conf import settings
from api.ml_utils import predict_fit
from api.models import Offer, Skill
import os
import pandas as pd
import matplotlib.pyplot as plt


def test_model_behavior():
    print("🧠 MODEL BEHAVIOR TEST — Does it make logical decisions?\n")

    offer = Offer.objects.first()
    if not offer:
        print("❌ No offers found in the DB — please run fake_data.py first.")
        return

    print(f"🎯 Testing against offer: {offer.title}")
    print(f"Field required: {offer.field_required}")
    required_skills = list(offer.required_skills.values_list('name', flat=True))
    print(f"Required skills ({len(required_skills)}): {required_skills}\n")

    # =====================================================================
    # Mock classes that properly simulate skill matching
    # =====================================================================

    class FakeSkillsQuerySet:
        """Mocks Django QuerySet for skills"""

        def __init__(self, skills_list):
            self._skills = skills_list

        def values_list(self, field, flat=False):
            return self._skills

    class FakeCerts:
        def __init__(self, n):
            self._n = n

        def count(self):
            return self._n

    class FakeProfile:
        def __init__(self, gpa, score, certs, field, skills_ratio):
            self.gpa = gpa
            self.score = score
            self.field_of_study = field
            self.certifications = FakeCerts(certs)

            # Calculate how many skills this candidate has
            num_skills = int(len(required_skills) * skills_ratio)
            self.skills = FakeSkillsQuerySet(required_skills[:num_skills])

    # =====================================================================
    # Test scenarios with proper skill mocking
    # =====================================================================

    scenarios = [
        {
            "name": "Perfect candidate",
            "skills_ratio": 1.0,  # Has ALL skills
            "gpa": 3.9,
            "score": 380,
            "certs": 3,
            "field_match": 1,
        },
        {
            "name": "Perfect skills but low score",
            "skills_ratio": 1.0,
            "gpa": 3.5,
            "score": 150,
            "certs": 2,
            "field_match": 1,
        },
        {
            "name": "Partial skills (50%), high score",
            "skills_ratio": 0.5,
            "gpa": 3.8,
            "score": 360,
            "certs": 2,
            "field_match": 1,
        },
        {
            "name": "Few skills (20%), high everything else",
            "skills_ratio": 0.2,
            "gpa": 3.9,
            "score": 300,
            "certs": 4,
            "field_match": 1,
        },
        {
            "name": "No skills, max score",
            "skills_ratio": 0.0,
            "gpa": 2.2,
            "score": 400,
            "certs": 0,
            "field_match": 1,
        },
        {
            "name": "Perfect skills, wrong field",
            "skills_ratio": 1.0,
            "gpa": 3.6,
            "score": 350,
            "certs": 2,
            "field_match": 0,
        },
        {
            "name": "Most skills (80%), good all-around",
            "skills_ratio": 0.8,
            "gpa": 3.7,
            "score": 340,
            "certs": 3,
            "field_match": 1,
        },
    ]

    # =====================================================================
    # Evaluate each scenario
    # =====================================================================

    results = []

    for s in scenarios:
        print(f"\n{'=' * 60}")
        print(f"Testing: {s['name']}")
        print('=' * 60)

        fake_profile = FakeProfile(
            gpa=s["gpa"],
            score=s["score"],
            certs=s["certs"],
            field=offer.field_required if s["field_match"] else "Business",
            skills_ratio=s["skills_ratio"]
        )

        # Use the main prediction function
        prob = predict_fit(fake_profile, offer)

        # Or use the simpler version:
        # prob = predict_fit_simple(fake_profile, offer, skill_match_override=s["skills_ratio"])

        results.append({
            "Scenario": s["name"],
            "Skills %": f"{s['skills_ratio'] * 100:.0f}%",
            "GPA": s["gpa"],
            "Score": s["score"],
            "Certs": s["certs"],
            "Field": "✓" if s["field_match"] else "✗",
            "Fit": prob,
        })

    # =====================================================================
    # Display results
    # =====================================================================

    df = pd.DataFrame(results)
    df = df.sort_values(by="Fit", ascending=False)

    print("\n" + "=" * 80)
    print("FINAL RESULTS".center(80))
    print("=" * 80)
    print(df.to_string(index=False))

    # Visualization
    plt.figure(figsize=(10, 6))
    colors = ['green' if x >= 0.7 else 'orange' if x >= 0.4 else 'red' for x in df["Fit"]]
    plt.barh(df["Scenario"], df["Fit"], color=colors)
    plt.gca().invert_yaxis()
    plt.xlabel("Predicted Fit Probability")
    plt.title("Model Decision Sanity Test")
    plt.axvline(x=0.7, color='green', linestyle='--', alpha=0.3, label='Strong')
    plt.axvline(x=0.4, color='orange', linestyle='--', alpha=0.3, label='Moderate')
    plt.legend()
    plt.tight_layout()
    plt.show()

    print("\n✅ Expected behavior:")
    print("   1. Perfect skills + high score → ~0.80-0.90")
    print("   2. Perfect skills + low score → ~0.65-0.75")
    print("   3. 50% skills + high score → ~0.45-0.55")
    print("   4. <30% skills → <0.30 (regardless of other factors)")
    print("   5. Wrong field should reduce by ~0.05-0.10")


if __name__ == "__main__":
    test_model_behavior()