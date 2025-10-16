import joblib
import numpy as np
import pandas as pd
import os
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

from api.models import Application
from django.conf import settings


MODEL_PATH = os.path.join(settings.BASE_DIR, "ml_model.pkl")
SCALER_PATH = os.path.join(settings.BASE_DIR, "scaler.pkl")


# ---------------------------------------------------------------------
# 🧩 Helper: skill match ratio
# ---------------------------------------------------------------------
def compute_skill_match_ratio(profile, offer):
    profile_skills = set(profile.skills.values_list("name", flat=True))
    offer_skills = set(offer.required_skills.values_list("name", flat=True))
    if not offer_skills:
        return 0.0
    return len(profile_skills & offer_skills) / len(offer_skills)


# ---------------------------------------------------------------------
# 🧠 Main training function
# ---------------------------------------------------------------------
def run_train():
    print("📦 Collecting applications...")
    apps = Application.objects.select_related("user__profile", "offer").all()
    data = []

    for app in apps:
        profile = app.user.profile
        offer = app.offer

        # basic fields
        gpa = float(profile.gpa or 0)
        score = float(profile.score or 0)
        skill_ratio = compute_skill_match_ratio(profile, offer)
        field_match = 1 if profile.field_of_study == offer.field_required else 0
        cert_count = profile.certifications.count() if hasattr(profile, "certifications") else 0

        # only accepted/rejected are used
        if app.status == "accepted":
            label = 1
        elif app.status == "rejected":
            label = 0
        else:
            continue

        data.append({
            "gpa": gpa,
            "score": score,
            "skill_match_ratio": skill_ratio,
            "field_match": field_match,
            "cert_count": cert_count,
            "field_of_study": profile.field_of_study,
            "field_required": offer.field_required,
            "label": label
        })

    df = pd.DataFrame(data)
    print(f"✅ Loaded {len(df)} samples after filtering pending apps")

    # One-hot encode categorical variables
    df = pd.get_dummies(df, columns=["field_of_study", "field_required"])

    # Balance dataset
    accepted = df[df["label"] == 1]
    rejected = df[df["label"] == 0]
    min_len = min(len(accepted), len(rejected))
    df_balanced = pd.concat([accepted.sample(min_len, random_state=42),
                             rejected.sample(min_len, random_state=42)])
    print(f"⚖️ Balanced dataset: {len(df_balanced)} samples ({min_len} each class)")

    X = df_balanced.drop("label", axis=1)
    y = df_balanced["label"]

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    # Model
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        class_weight="balanced_subsample",
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # 🧮 Training & test accuracy
    y_train_pred = model.predict(X_train)
    train_acc = accuracy_score(y_train, y_train_pred)
    print(f"🏋️ Training accuracy: {train_acc:.3f}")

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f"🎯 Test accuracy: {acc:.3f} | F1-score: {f1:.3f}")
    print(classification_report(y_test, y_pred))

    # 🧩 Cross-validation
    cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring="accuracy")
    print(f"🧩 5-fold CV mean: {cv_scores.mean():.3f} | std: {cv_scores.std():.3f}")

    # 📈 ROC-AUC
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"📊 ROC-AUC: {auc:.3f}")

    # 🔍 Feature importance
    importances = model.feature_importances_
    feat_df = pd.DataFrame({
        "Feature": X.columns,
        "Importance": importances
    }).sort_values("Importance", ascending=False)

    print("\n🔝 Top Features:")
    print(feat_df.head(10))

    # Plot feature importance
    plt.figure(figsize=(10, 6))
    plt.barh(feat_df["Feature"], feat_df["Importance"])
    plt.gca().invert_yaxis()
    plt.title("Feature Importance")
    plt.tight_layout()
    plt.show()

    # 💾 Save model & scaler
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print("💾 Model and scaler saved!")
