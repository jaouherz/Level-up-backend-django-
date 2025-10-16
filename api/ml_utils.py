import joblib
import os
import numpy as np
import warnings
from django.conf import settings

MODEL_PATH = os.path.join(settings.BASE_DIR, "ml_model.pkl")
SCALER_PATH = os.path.join(settings.BASE_DIR, "scaler.pkl")

model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)


def compute_skill_match_ratio(profile, offer):
    """Calculate what % of required skills the candidate has"""
    profile_skills = set(profile.skills.values_list("name", flat=True))
    offer_skills = set(offer.required_skills.values_list("name", flat=True))

    if not offer_skills:
        return 1.0

    match_ratio = len(profile_skills & offer_skills) / len(offer_skills)
    print(f"  🔍 Skills: {len(profile_skills & offer_skills)}/{len(offer_skills)} = {match_ratio:.2f}")
    return match_ratio


def predict_fit(profile, offer):
    """
    Enhanced predictive logic:
    - Keeps your tier system and nuanced weighting
    - Adds relevance check for certifications (based on linked skills)
    """

    # ========== Extract & Normalize ==========
    field_of_study = profile.field_of_study or ""
    field_required = offer.field_required or ""

    skill_match = compute_skill_match_ratio(profile, offer)
    field_match = int(field_of_study == field_required)
    gpa = float(profile.gpa or 0)
    score = float(profile.score or 0)

    # ✅ NEW: Only count certifications that match offer's required skills
    offer_skills = set(offer.required_skills.values_list("name", flat=True))
    matching_certs = 0
    total_certs = profile.certifications.count() if hasattr(profile, "certifications") else 0

    for cert in profile.certifications.all():
        cert_skills = set(cert.skills.values_list("name", flat=True))
        if cert_skills & offer_skills:
            matching_certs += 1

    relevant_cert_ratio = matching_certs / max(total_certs, 1)
    norm_certs = np.clip(relevant_cert_ratio, 0, 1)  # weight based on matching ones

    norm_score = np.clip(score / 400.0, 0, 1)
    norm_gpa = np.clip(gpa / 4.0, 0, 1)

    print(f"  📊 Normalized: Score={norm_score:.2f}, GPA={norm_gpa:.2f}, "
          f"Certs(relevant)={norm_certs:.2f}, Field={field_match}")

    # ========== Tiered Logic (same as before) ==========
    if skill_match < 0.4:
        base = 0.08 + 0.20 * skill_match + 0.10 * norm_score + 0.02 * norm_certs
        print(f"  ⚠️  Tier 1: Missing critical skills")

    elif skill_match < 0.75:
        base = 0.30 + 0.28 * skill_match + 0.25 * norm_score + 0.12 * field_match + 0.03 * norm_gpa + 0.04 * norm_certs
        print(f"  ⚡ Tier 2: Partial skill match")

        if norm_score >= 0.85 and norm_certs >= 0.4:
            base += 0.05
            print(f"  🎯 Bonus: High performer compensating")

    else:
        base = 0.45 + 0.20 * skill_match + 0.25 * norm_score + 0.10 * field_match + 0.03 * norm_gpa + 0.04 * norm_certs
        print(f"  ✨ Tier 3: Strong skill match")

    # --- same bonuses/penalties ---
    if skill_match == 1.0 and norm_score >= 0.90 and field_match == 1:
        base += 0.08
        print(f"  🌟 BONUS: Dream candidate!")
    elif skill_match == 1.0 and norm_score >= 0.85:
        base += 0.05
        print(f"  🎯 BONUS: Excellent candidate")
    elif skill_match == 1.0 and norm_score >= 0.60:
        base += 0.03
        print(f"  ✓ BONUS: Strong candidate")
    elif skill_match >= 0.80 and norm_score >= 0.85:
        base += 0.05
        print(f"  🎯 BONUS: High performer")
    elif skill_match >= 0.85:
        base += 0.02
        print(f"  ✓ BONUS: Near-complete skills")

    # --- penalties ---
    if field_match == 0:
        if skill_match < 0.75:
            base -= 0.10
            print(f"  ⚠️  PENALTY: Field mismatch + incomplete skills")
        else:
            base -= 0.08
            print(f"  ⚠️  PENALTY: Field mismatch")
    if norm_score < 0.40:
        penalty = 0.10 if skill_match >= 0.8 else 0.08
        base -= penalty
        print(f"  ⚠️  PENALTY: Low performance score")
    if 0.75 <= skill_match < 1.0:
        base -= 0.03
        print(f"  ⚠️  Small penalty: Not quite all skills")

    # --- certification bonuses (relevant ones only) ---
    if matching_certs >= 5:
        base += 0.04
        print(f"  📜 BONUS: Exceptional relevant certifications (5+)")
    elif matching_certs >= 3:
        base += 0.03
        print(f"  📜 BONUS: Strong relevant certifications (3-4)")
    elif matching_certs >= 1 and skill_match < 0.8:
        base += 0.02
        print(f"  📜 BONUS: Relevant certs helping borderline case")

    print(f"  💡 Logic score: {base:.3f}")

    final = np.clip(base, 0.05, 0.98)
    print(f"  ✅ Final: {final:.3f}\n")
    return round(float(final), 3)



# ========== ALTERNATIVE: Simplified Weighted Model ==========
def predict_fit_weighted(profile, offer, skill_match_override=None):
    """
    Cleaner weighted model with dynamic weights based on skill level
    """

    if skill_match_override is not None:
        skill_match = skill_match_override
    else:
        skill_match = compute_skill_match_ratio(profile, offer)

    field_match = int((profile.field_of_study or "") == (offer.field_required or ""))
    cert_count = profile.certifications.count() if hasattr(profile, "certifications") else 0

    gpa = np.clip(float(profile.gpa or 0) / 4.0, 0, 1)
    score = np.clip(float(profile.score or 0) / 400.0, 0, 1)
    certs = np.clip(cert_count / 5.0, 0, 1)

    # Dynamic weighting: as skills decrease, score becomes more important
    if skill_match >= 0.8:
        # Strong skills: score differentiates excellence
        w_skill, w_score, w_field, w_cert, w_gpa = 0.35, 0.30, 0.15, 0.12, 0.08
    elif skill_match >= 0.5:
        # Moderate skills: everything matters
        w_skill, w_score, w_field, w_cert, w_gpa = 0.40, 0.25, 0.15, 0.12, 0.08
    else:
        # Low skills: hard to compensate
        w_skill, w_score, w_field, w_cert, w_gpa = 0.55, 0.20, 0.12, 0.08, 0.05

    fit = (w_skill * skill_match + w_score * score + w_field * field_match +
           w_cert * certs + w_gpa * gpa)

    # Bonuses
    if skill_match == 1.0 and score >= 0.90:
        fit += 0.12
    elif skill_match >= 0.8 and score >= 0.85:
        fit += 0.08

    # Penalties
    if field_match == 0 and skill_match < 0.8:
        fit -= 0.08
    if score < 0.4:
        fit -= 0.06

    return round(float(np.clip(fit, 0.05, 0.98)), 3)