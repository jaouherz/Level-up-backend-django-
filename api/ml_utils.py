import joblib
import os
import numpy as np
from django.conf import settings
from django.utils import timezone

# ==========================
# Load ML model & scaler
# ==========================
MODEL_PATH = os.path.join(settings.BASE_DIR, "ml_model.pkl")
SCALER_PATH = os.path.join(settings.BASE_DIR, "scaler.pkl")

model = None
scaler = None

if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
    import joblib
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
else:
    print("⚠️ Model not found yet — training required.")

# ==========================
#  Feature extraction helpers
# ==========================
def compute_skill_match_ratio(profile, offer):
    """Calculate the % of required skills the candidate has."""
    profile_skills = set(profile.skills.values_list("name", flat=True))
    offer_skills = set(offer.required_skills.values_list("name", flat=True))
    if not offer_skills:
        return 1.0
    return len(profile_skills & offer_skills) / len(offer_skills)

def compute_certification_match_ratio(profile, offer):
    """How many certifications match required skills."""
    offer_skills = set(offer.required_skills.values_list("name", flat=True))
    matching_certs = 0
    total_certs = profile.certifications.count()

    for cert in profile.certifications.all():
        cert_skills = set(cert.skills.values_list("name", flat=True))
        if cert_skills & offer_skills:
            matching_certs += 1

    cert_ratio = matching_certs / max(total_certs, 1)
    return matching_certs, cert_ratio, total_certs

# ==========================
#  Feature vector (Fixed structure)
# ==========================
FEATURE_NAMES = [
    "gpa",
    "score",
    "skill_match_ratio",
    "field_match",
    "cert_ratio",
    "location_match"
]
import pandas as pd
def build_feature_vector(profile, offer):
    gpa = np.clip(float(profile.gpa or 0) / 4.0, 0, 1)
    score = np.clip(float(profile.score or 0) / 400.0, 0, 1)
    skill_match = compute_skill_match_ratio(profile, offer)
    field_match = int((profile.field_of_study or "").strip() == (offer.field_required or "").strip())
    matching_certs, cert_ratio, _ = compute_certification_match_ratio(profile, offer)

    location_match = 0
    if profile.university and offer.location:
        if profile.university.city.strip().lower() == offer.location.strip().lower():
            location_match = 1

    data = [[gpa, score, skill_match, field_match, cert_ratio, location_match]]
    X = pd.DataFrame(data, columns=FEATURE_NAMES)
    return X

# ==========================
#  Extract features (for rule engine)
# ==========================
def extract_features(profile, offer):
    gpa = float(profile.gpa or 0)
    score = float(profile.score or 0)
    skill_match = compute_skill_match_ratio(profile, offer)
    field_match = int((profile.field_of_study or "").strip() == (offer.field_required or "").strip())
    matching_certs, cert_ratio, total_certs = compute_certification_match_ratio(profile, offer)

    location_match = 0
    if profile.university and offer.location:
        if profile.university.city.strip().lower() == offer.location.strip().lower():
            location_match = 1

    deadline_passed = 1 if offer.deadline and offer.deadline < timezone.now().date() else 0

    return {
        "gpa": gpa,
        "score": score,
        "skill_match": skill_match,
        "field_match": field_match,
        "cert_ratio": cert_ratio,
        "cert_count": total_certs,
        "location_match": location_match,
        "deadline_passed": deadline_passed
    }

# ==========================
#  Base ML Prediction
# ==========================
def compute_base_fit(profile, offer):
    X = build_feature_vector(profile, offer)
    X_scaled = scaler.transform(X)
    prob = model.predict_proba(X_scaled)[0][1]
    return prob

# ==========================
#  Rule Engine
# ==========================
def apply_rules(features, base_prob):
    prob = base_prob

    # GPA bonus
    if features["gpa"] >= 3.5:
        prob += 0.1
    elif features["gpa"] >= 3.0:
        prob += 0.05

    if features["skill_match"] == 1.0:
        prob += 0.15
    elif features["skill_match"] >= 0.7:
        prob += 0.1

    # Score bonus (based on raw score)
    score_bonus = (features["score"] / 400.0) * 0.15
    prob += score_bonus

    # Field match
    if features["field_match"]:
        prob += 0.20
    else:
        pass

    # Location match
    if features["location_match"]:
        prob += 0.05

    # Certification bonus
    if features["cert_count"] >= 5:
        prob += 0.04
    elif features["cert_count"] >= 3:
        prob += 0.02
    elif features["cert_count"] >= 1:
        prob += 0.01

    # Deadline penalty
    if features["deadline_passed"]:
        prob = 0.0

    return max(0.05, min(prob, 0.98))

# ==========================
#  Final fit calculation
# ==========================
def predict_fit(profile, offer):
    features = extract_features(profile, offer)
    base_prob = compute_base_fit(profile, offer)
    final_prob = apply_rules(features, base_prob)
    return round(final_prob, 3)
