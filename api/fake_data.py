from django.contrib.auth.models import User
from api.models import Skill, University, Offer, Profile, Application, Certification
from django.db import connection
import random
import string
from time import time
from collections import Counter

# ==============================================================
# 🔸 Utility
# ==============================================================

def random_username(i):
    return f"user_{i}_{''.join(random.choices(string.ascii_lowercase, k=5))}"


# ==============================================================
# 🧹 Main Seeder
# ==============================================================

def run():
    start = time()
    print("🧹 Clearing old data...")
    Application.objects.all()._raw_delete(using=connection.alias)
    # Clear M2M relations explicitly before Offer
    Offer.required_skills.through.objects.all()._raw_delete(using=connection.alias)
    Offer.objects.all()._raw_delete(using=connection.alias)
    Profile.skills.through.objects.all()._raw_delete(using=connection.alias)
    Profile.certifications.through.objects.all()._raw_delete(using=connection.alias)
    Profile.objects.all()._raw_delete(using=connection.alias)
    University.objects.all()._raw_delete(using=connection.alias)
    Skill.objects.all()._raw_delete(using=connection.alias)
    Certification.objects.all()._raw_delete(using=connection.alias)
    User.objects.exclude(is_superuser=True)._raw_delete(using=connection.alias)

    # ---- skills ----
    print("⚙️ Creating skills...")
    skill_names = ["Python", "Java", "C++", "ML", "Data", "Web", "React", "DevOps", "Cloud", "Cybersec"]
    skills = [Skill.objects.create(name=s) for s in skill_names]

    # ---- certifications ----
    print("🎓 Creating certifications...")
    cert_names = [
        "AWS Certified Developer", "Azure Fundamentals", "Google Cloud Associate",
        "Oracle Java SE8", "CompTIA Security+", "Docker Certified",
        "Jenkins CI/CD Specialist", "Kubernetes Administrator",
        "TensorFlow Developer", "Linux Foundation Certified"
    ]
    certs = [Certification.objects.create(name=c) for c in cert_names]

    # ---- auto link certs to skills (Groq logic integrated)
    print("🤖 Linking certs to skills...")
    from api.cert_skill_auto_link import auto_link_certifications
    auto_link_certifications()

    # ---- university ----
    uni = University.objects.create(
        name="University of Tunis El Manar",
        city="Tunis", country="Tunisia",
        website="https://utm.tn", email_domain="utm.tn"
    )

    # ---- recruiters ----
    print("🏢 Creating recruiters...")
    rec_users = [User(username=f"recruiter{i}") for i in range(10)]
    User.objects.bulk_create(rec_users, batch_size=1000)
    rec_users = list(User.objects.filter(username__startswith="recruiter"))
    rec_profiles = [Profile(user=u, role="recruiter") for u in rec_users]
    Profile.objects.bulk_create(rec_profiles, batch_size=1000)

    # ---- students ----
    NUM_STUDENTS = 25000
    print(f"👩‍🎓 Creating {NUM_STUDENTS} students...")
    users = [User(username=random_username(i)) for i in range(NUM_STUDENTS)]
    User.objects.bulk_create(users, batch_size=2000)
    users = list(User.objects.filter(username__startswith="user_"))

    profiles = []
    for u in users:
        profiles.append(Profile(
            user=u,
            role="student",
            university=uni,
            field_of_study=random.choice(["CS", "IT", "Software Engineering"]),
            gpa=round(random.uniform(2.0, 4.0), 2),
            score=random.randint(100, 400)
        ))
    Profile.objects.bulk_create(profiles, batch_size=2000)

    # ---- assign random skills ----
    print("🔗 Assigning skills to students...")
    all_profiles = list(Profile.objects.filter(role="student").values_list("id", flat=True))
    through_model = Profile.skills.through
    m2m = []
    for pid in all_profiles:
        for s in random.sample(skills, random.randint(1, 5)):
            m2m.append(through_model(profile_id=pid, skill_id=s.id))
    through_model.objects.bulk_create(m2m, batch_size=5000)

    # ---- assign certifications ----
    print("🎖 Assigning certifications to students...")
    cert_through = Profile.certifications.through
    m2m_cert = []
    for pid in all_profiles:
        for c in random.sample(certs, random.randint(0, 3)):
            m2m_cert.append(cert_through(profile_id=pid, certification_id=c.id))
    cert_through.objects.bulk_create(m2m_cert, batch_size=5000)

    # ---- offers ----
    print("📄 Creating offers...")
    offers = []
    for i in range(200):
        offers.append(Offer(
            title=f"Internship {i}",
            company=f"Company {i}",
            description="Test internship",
            field_required=random.choice(["CS", "IT", "Software Engineering"]),
            level_required="intern",
            location="Tunis",
            created_by=random.choice(rec_users),
            verified_by_university=uni,
        ))
    Offer.objects.bulk_create(offers, batch_size=500)
    offers = list(Offer.objects.all())
    for o in offers:
        o.required_skills.set(random.sample(skills, random.randint(2, 4)))

    # ---- applications ----
    print("📨 Creating applications...")
    applications = []
    for prof in Profile.objects.filter(role="student").iterator(chunk_size=5000):
        student_skills = set(prof.skills.values_list("id", flat=True))
        student_certs = prof.certifications.count()
        for offer in random.sample(offers, random.randint(1, 5)):
            offer_skills = set(offer.required_skills.values_list("id", flat=True))
            if not offer_skills:
                continue

            # Calculate fit
            skill_ratio = len(student_skills & offer_skills) / len(offer_skills)
            gpa_score = float(prof.gpa or 0) / 4.0
            score_norm = float(prof.score or 0) / 400.0
            cert_bonus = min(student_certs * 0.05, 0.2)

            fit_score = (
                0.35 * skill_ratio +
                0.25 * gpa_score +
                0.25 * score_norm +
                0.15 * cert_bonus
            )

            fit_score += random.uniform(-0.25, 0.25)
            fit_score += random.uniform(-0.1, 0.1)
            fit_score = max(0, min(fit_score, 1))

            # Assign status
            if fit_score > 0.7:
                status = random.choices(["accepted", "rejected"], weights=[0.8, 0.2])[0]
            elif fit_score > 0.4:
                status = random.choices(["accepted", "pending", "rejected"], weights=[0.4, 0.3, 0.3])[0]
            else:
                status = random.choices(["rejected", "accepted"], weights=[0.8, 0.2])[0]

            applications.append(Application(user=prof.user, offer=offer, status=status))

    print(f"🧮 Total applications to insert: {len(applications)}")
    Application.objects.bulk_create(applications, batch_size=5000)

    print(f"✅ Done in {round(time() - start, 2)}s")
    print("📊 Status distribution:", Counter([a.status for a in applications]))
