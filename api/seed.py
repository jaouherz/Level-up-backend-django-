import sys
import os
import django
import random 
# Add project root to PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

django.setup()


from faker import Faker

from api.models import (
    User, Profile, Skill, Company, Offer, Application,
    Feedback, ScoreHistory, University, Certification
)
from django.utils import timezone

fake = Faker()

def run():
    print("Seeding database...")

    # -------------------------------------------------------------
    # SKILLS
    # -------------------------------------------------------------
    skill_names = ["Python", "Django", "ML", "Flutter", "Java", "AWS", "DevOps", "Angular"]
    skills = [Skill.objects.get_or_create(name=s)[0] for s in skill_names]

    # -------------------------------------------------------------
    # UNIVERSITIES
    # -------------------------------------------------------------
    universities = []
    for _ in range(5):
        uni = University.objects.create(
            name=fake.company() + " University",
            city=fake.city(),
            country=fake.country(),
            website=fake.url(),
            email_domain=f"{fake.lexify(text='????')}.edu"
        )
        universities.append(uni)

    # -------------------------------------------------------------
    # COMPANIES
    # -------------------------------------------------------------
    companies = []
    for _ in range(10):
        c = Company.objects.create(
            name=fake.company(),
            industry=fake.job(),
            website=fake.url(),
            city=fake.city(),
            country=fake.country()
        )
        companies.append(c)

    # -------------------------------------------------------------
    # USERS + PROFILES
    # -------------------------------------------------------------
    users = []
    for _ in range(30):
        email = fake.email()
        user = User.objects.create_user(
            email=email,
            password="123456",
            first_name=fake.first_name(),
            last_name=fake.last_name()
        )
        users.append(user)

        profile = Profile.objects.create(
            user=user,
            role=random.choice(["student", "recruiter", "university"]),
            university=random.choice(universities),
            field_of_study=fake.job(),
            gpa=round(random.uniform(2.0, 4.0), 2)
        )
        profile.skills.add(*random.sample(skills, k=random.randint(1, 4)))

    # -------------------------------------------------------------
    # CERTIFICATIONS
    # -------------------------------------------------------------
    for _ in range(10):
        cert = Certification.objects.create(
            name=fake.catch_phrase(),
            issuer=fake.company(),
            issued_at=fake.date_between(start_date='-2y', end_date='today'),
            level=random.choice(["Beginner", "Intermediate", "Advanced"])
        )
        cert.skills.add(*random.sample(skills, k=random.randint(1, 3)))

    # -------------------------------------------------------------
    # OFFERS
    # -------------------------------------------------------------
    offers = []
    for _ in range(20):
        offer = Offer.objects.create(
            title=fake.job(),
            company=random.choice(companies),
            description=fake.text(),
            field_required=fake.job(),
            level_required=random.choice(["intern", "junior", "senior"]),
            location=fake.city(),
            deadline=fake.date_between(start_date='today', end_date='+90d'),
            created_by=random.choice(users),
            verified_by_university=random.choice(universities)
        )
        offer.required_skills.add(*random.sample(skills, k=random.randint(1, 4)))
        offers.append(offer)

    # -------------------------------------------------------------
    # APPLICATIONS
    # -------------------------------------------------------------
    applications = []
    for user in users:
        for offer in random.sample(offers, k=random.randint(1, 5)):
            app, created = Application.objects.get_or_create(
                user=user,
                offer=offer,
                defaults={
                    "status": random.choice(["pending", "accepted", "rejected"]),
                    "predicted_fit": round(random.uniform(0, 1), 2),
                    "final_rank": random.randint(1, 10)
                }
            )
            applications.append(app)

    # -------------------------------------------------------------
    # FEEDBACK
    # -------------------------------------------------------------
    for app in applications:
        if random.random() > 0.7:  # 30% chance
            Feedback.objects.create(
                application=app,
                recruiter=random.choice(users),
                feedback_type=random.choice(["negative", "neutral"]),
                comment=fake.sentence()
            )

    # -------------------------------------------------------------
    # SCORE HISTORY
    # -------------------------------------------------------------
    for user in users:
        ScoreHistory.objects.create(
            user=user,
            reason="Auto score",
            points=random.randint(1, 50)
        )

    print("Seeding completed!")

if __name__ == "__main__":
    run()
