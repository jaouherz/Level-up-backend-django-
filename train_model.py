import os
import django
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    roc_auc_score
)

# ============================
# Django setup (important to run outside manage.py shell)
# ============================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")  # ⚠️ update to your settings module
django.setup()

from api.models import Application

MODEL_PATH = os.path.join(os.getcwd(), "ml_model.pkl")
SCALER_PATH = os.path.join(os.getcwd(), "scaler.pkl")


# ---------------------------------------------------------------------
# 🧩 Helper functions
# ---------------------------------------------------------------------
def compute_skill_match_ratio(profile, offer):
    profile_skills = set(profile.skills.values_list("name", flat=True))
    offer_skills = set(offer.required_skills.values_list("name", flat=True))
    if not offer_skills:
        return 0.0
    return len(profile_skills & offer_skills) / len(offer_skills)


def compute_cert_match_ratio(profile, offer):
    """Certifications that have skills matching offer's required skills."""
    offer_skills = set(offer.required_skills.values_list("name", flat=True))
    total_certs = profile.certifications.count() if hasattr(profile, "certifications") else 0
    matching = 0

    for cert in profile.certifications.all():
        cert_skills = set(cert.skills.values_list("name", flat=True))
        if cert_skills & offer_skills:
            matching += 1

    return matching, total_certs



def run_train():
    print("📦 Collecting applications...")
    apps = Application.objects.select_related("user__profile", "offer").all()
    data = []

    for app in apps:
        profile = app.user.profile
        offer = app.offer


        if app.status == "accepted":
            label = 1
        elif app.status == "rejected":
            label = 0
        else:
            continue

        gpa = float(profile.gpa or 0)
        score = float(profile.score or 0)
        skill_ratio = min(compute_skill_match_ratio(profile, offer), 0.6)
        field_match = 1 if profile.field_of_study == offer.field_required else 0

        cert_matching, cert_total = compute_cert_match_ratio(profile, offer)
        cert_ratio = cert_matching / max(cert_total, 1)

        location_match = 0
        if profile.university and offer.location:
            if profile.university.city.strip().lower() == offer.location.strip().lower():
                location_match = 1

        data.append({
            "gpa": gpa,
            "score": score,
            "skill_match_ratio": skill_ratio,
            "field_match": field_match,
            "cert_ratio": cert_ratio,
            "location_match": location_match,
            "label": label
        })

    df = pd.DataFrame(data)
    print(f"✅ Loaded {len(df)} samples after filtering pending apps")

    if df.empty:
        print("❌ No accepted/rejected data to train on.")
        return

    # One-hot encode categorical fields
    #df = pd.get_dummies(df, columns=["field_of_study", "field_required"], drop_first=True)

    # Balance dataset
    accepted = df[df["label"] == 1]
    rejected = df[df["label"] == 0]
    min_len = min(len(accepted), len(rejected))
    df_balanced = pd.concat([
        accepted.sample(min_len, random_state=42),
        rejected.sample(min_len, random_state=42)
    ])
    print(f"⚖️ Balanced dataset: {len(df_balanced)} samples ({min_len} each class)")

    X = df_balanced.drop("label", axis=1)
    import json

    # Save feature column order
    FEATURE_COLS_PATH = os.path.join(os.getcwd(), "feature_columns.json")
    with open(FEATURE_COLS_PATH, "w") as f:
        json.dump(list(X.columns), f)
    print(f"📝 Feature columns saved to {FEATURE_COLS_PATH}")
    y = df_balanced["label"]

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    # Train model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced_subsample",
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # 🧮 Evaluate
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred_test)
    f1 = f1_score(y_test, y_pred_test)

    print(f"🏋️ Training accuracy: {train_acc:.3f}")
    print(f"🎯 Test accuracy: {test_acc:.3f} | F1-score: {f1:.3f}")
    print(classification_report(y_test, y_pred_test))

    # CV
    cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring="accuracy")
    print(f"🧪 5-fold CV mean: {cv_scores.mean():.3f} | std: {cv_scores.std():.3f}")

    # ROC-AUC
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"📊 ROC-AUC: {auc:.3f}")

    # Feature importance
    feat_df = pd.DataFrame({
        "Feature": X.columns,
        "Importance": model.feature_importances_
    }).sort_values("Importance", ascending=False)

    print("\n🔝 Top Features:")
    print(feat_df.head(10))

    # Plot
    plt.figure(figsize=(10, 6))
    plt.barh(feat_df["Feature"], feat_df["Importance"])
    plt.gca().invert_yaxis()
    plt.title("Feature Importance")
    plt.tight_layout()
    plt.show()

    # Save model & scaler
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"💾 Model and scaler saved to:\n  {MODEL_PATH}\n  {SCALER_PATH}")


# Run training if file executed directly
if __name__ == "__main__":
    run_train()
