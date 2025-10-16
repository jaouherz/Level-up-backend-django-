from django.contrib.auth.models import User
from api.models import Skill, University, Offer, Profile, Application, Certification
from django.db import transaction
import random
import string
from time import time

def random_username(i):
    return f"user_{i}_{''.join(random.choices(string.ascii_lowercase, k=5))}"

@transaction.atomic
def run():
    start = time()
    print("🧹 Clearing old data...")
    Application.objects.all().delete()
    Offer.objects.all().delete()
    Profile.objects.all().delete()
    University.objects.all().delete()
    Skill.objects.all().delete()
    Certification.objects.all().delete()
    User.objects.exclude(is_superuser=True).delete()

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
    print("🔗 Assigning skills...")
    all_profiles = list(Profile.objects.filter(role="student").values_list("id", flat=True))
    through_model = Profile.skills.through
    m2m = []
    for pid in all_profiles:
        for s in random.sample(skills, random.randint(1, 5)):
            m2m.append(through_model(profile_id=pid, skill_id=s.id))
    through_model.objects.bulk_create(m2m, batch_size=5000)

    # ---- assign certifications ----
    print("🎖 Assigning certifications...")
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

    # ---- applications with realistic statuses ----
    # ---- applications with realistic statuses ----
    print("📨 Creating applications...")
    applications = []
    for prof in Profile.objects.filter(role="student")[:25000]:
        student_skills = set(prof.skills.values_list("id", flat=True))
        student_certs = prof.certifications.count()
        for offer in random.sample(offers, random.randint(1, 5)):
            offer_skills = set(offer.required_skills.values_list("id", flat=True))
            if not offer_skills:
                continue

            # calculate realistic fit score
            skill_ratio = len(student_skills & offer_skills) / len(offer_skills)
            gpa_score = float(prof.gpa or 0) / 4.0
            score_norm = float(prof.score or 0) / 400.0
            cert_bonus = min(student_certs * 0.05, 0.2)  # cap at +0.2

            # combined weighted score
            fit_score = (
                    0.5 * skill_ratio +
                    0.25 * gpa_score +
                    0.15 * score_norm +
                    0.1 * cert_bonus
            )

            # --- NEW realism tweaks ---
            # Add slight randomness (±0.15)
            fit_score += random.uniform(-0.15, 0.15)

            # Add company bias (some companies stricter)
            company_bias = random.uniform(-0.05, 0.05)
            fit_score += company_bias

            # Clamp between 0–1
            fit_score = max(0, min(fit_score, 1))

            # Status thresholds
            if fit_score > 0.7:
                status = "accepted"
            elif fit_score > 0.4:
                status = "pending"
            else:
                status = "rejected"

            applications.append(Application(user=prof.user, offer=offer, status=status))

    Application.objects.bulk_create(applications, batch_size=5000)
    print(f"✅ {len(applications)} applications inserted.")
    print(f"🎉 Done in {round(time()-start,2)}s")
