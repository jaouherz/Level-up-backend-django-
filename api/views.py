from datetime import date, datetime

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model, logout, login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from api.forms import RegisterForm, LoginForm

User = get_user_model()
from rest_framework import viewsets, status, mixins, permissions
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny , IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api.models import (
    Application, Offer, Profile, Skill, Certification,
    University, ScoreHistory, Feedback, Company, InternshipDemand
)
from api.serializers import (
    ApplicationSerializer, ProfileSerializer, OfferSerializer,
    SkillSerializer, CertificationSerializer, UniversitySerializer,
    ScoreHistorySerializer, FeedbackSerializer, RegisterSerializer, EmailTokenObtainPairSerializer, CompanySerializer,
    InternshipDemandSerializer
)
from api.ml_utils import predict_fit


# =========================
# 📩 APPLICATIONS
# =========================
class ApplicationViewSet(viewsets.GenericViewSet,
                         mixins.CreateModelMixin,
                         mixins.ListModelMixin,
                         mixins.RetrieveModelMixin):
    queryset = Application.objects.select_related("user", "offer").all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]  # 🔒 secure

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_fake(self, request, pk=None):
        try:
            app = self.get_object()
        except Application.DoesNotExist:
            return Response({"error": "Application not found"}, status=404)

        # (Optionally: restrict to recruiters/admins)
        # if getattr(request.user.profile, "role", "student") not in ("recruiter", "admin"):
        #     return Response({"detail": "Forbidden"}, status=403)

        app.is_fake = True
        app.save()

        profile = app.user.profile
        decrement_points = 10
        profile.score = max(0, profile.score - decrement_points)
        profile.save()

        ScoreHistory.objects.create(
            user=app.user,
            reason="Fake profile or skills detected",
            points=-decrement_points
        )

        count = replace_fake_candidates(app.offer.id)
        return Response({
            "message": f"Candidate {app.user.email} marked as fake.",
            "score_decrement": decrement_points,
            "replacements_made": count
        }, status=200)

    def create(self, request, *args, **kwargs):
        """
        Hardened: use the authenticated user instead of accepting an arbitrary user_id.
        """
        offer_id = request.data.get("offer_id")
        if not offer_id:
            return Response({"error": "offer_id is required"}, status=400)

        user = request.user  # 🔒 don’t let a client apply on behalf of another user

        try:
            offer = Offer.objects.get(pk=offer_id)
        except Offer.DoesNotExist:
            return Response({"error": f"Offer {offer_id} not found"}, status=404)

        today = date.today()
        if offer.is_closed:
            return Response({"error": "This offer is closed"}, status=400)

        if offer.deadline and today > offer.deadline:
            if not (offer.extended_deadline and today <= offer.extended_deadline):
                return Response({"error": "This offer is expired"}, status=400)

        profile = user.profile
        fit_score = predict_fit(profile, offer)

        app, created = Application.objects.update_or_create(
            user=user,
            offer=offer,
            defaults={"predicted_fit": fit_score, "status": "pending"}
        )

        return Response({
            "message": "Application created" if created else "Application updated",
            "user":  user.email,
            "offer": offer.title,
            "predicted_fit": round(fit_score, 3),
            "id": app.id
        }, status=201 if created else 200)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_applications(self, request):
        user = request.user

        apps = Application.objects.filter(user=user).select_related("offer").order_by("-id")

        serializer = ApplicationSerializer(apps, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def accept(self, request, pk=None):
        """Recruiter accepts a student application."""
        app = self.get_object()
        profile = request.user.profile

        if profile.role != "recruiter":
            return Response({"error": "Only recruiters can accept applications."}, status=403)

        if app.offer.company != profile.company:
            return Response({"error": "You are not allowed to manage this offer."}, status=403)

        app.status = "accepted"
        app.save()

        return Response({"message": f"Application of {app.user.email} accepted for {app.offer.title}."})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Recruiter rejects a student application."""
        app = self.get_object()
        profile = request.user.profile

        if profile.role != "recruiter":
            return Response({"error": "Only recruiters can reject applications."}, status=403)

        if app.offer.company != profile.company:
            return Response({"error": "You are not allowed to manage this offer."}, status=403)

        app.status = "rejected"
        app.save()

        return Response({"message": f"Application of {app.user.email} rejected for {app.offer.title}."})


# =========================
# 👤 PROFILES
# =========================
class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user').prefetch_related('skills', 'certifications')
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

   
    def create(self, request, *args, **kwargs):
        user = request.user
        data = request.data

        profile, _ = Profile.objects.get_or_create(user=user)
        self._update_profile_fields(profile, data)

        return Response({
            "message": "Profile created/updated",
            "id": profile.id,
            "user": user.email,
            "role": profile.role,
            "skills": [s.name for s in profile.skills.all()],
            "certifications": [c.name for c in profile.certifications.all()],
        })

   
    @action(detail=False, methods=["get"], url_path="my-profile")
    def my_profile(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    
    @action(detail=False, methods=["patch"], url_path="update-my-profile")
    def update_my_profile(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)

        data = request.data
        self._update_profile_fields(profile, data)

        serializer = self.get_serializer(profile)
        return Response({
            "message": "Profile updated successfully",
            "profile": serializer.data
        })

   
    def _update_profile_fields(self, profile, data):
        profile.field_of_study = data.get("field_of_study", profile.field_of_study)
        #profile.gpa = data.get("gpa", profile.gpa)
        #profile.score = data.get("score", profile.score)
        #profile.role = data.get("role", profile.role)

        profile.save()

        if "skills" in data:
            skills = [Skill.objects.get_or_create(name=s)[0] for s in data["skills"]]
            profile.skills.set(skills)

        if "certifications" in data:
            certs = [Certification.objects.get_or_create(name=c)[0] for c in data["certifications"]]
            profile.certifications.set(certs)

        profile.save()
        return profile

# =========================
# 📊 RANKING / REPLACEMENTS
# =========================
@api_view(["GET"])
@permission_classes([IsAuthenticated])  # 🔒 secure
def ranked_candidates(request, offer_id):
    try:
        offer = Offer.objects.get(id=offer_id)
    except Offer.DoesNotExist:
        return Response({"error": "Offer not found"}, status=404)

    apps = (
        Application.objects
        .filter(offer=offer)
        .select_related("user__profile", "offer")
        .order_by("-predicted_fit")
    )

    if not apps.exists():
        return Response({"error": "No applications found for this offer."}, status=404)

    candidates = [
        {
            "email": a.user.email,
            "field_of_study": getattr(a.user.profile, "field_of_study", None),
            "gpa": getattr(a.user.profile, "gpa", None),
            "score": getattr(a.user.profile, "score", None),
            "predicted_fit": a.predicted_fit,
        }
        for a in apps
    ]

    return Response({
        "offer": offer.title,
        "total_candidates": len(candidates),
        "candidates": candidates
    })


def replace_fake_candidates(offer_id):
    fake_apps = Application.objects.filter(
        offer_id=offer_id,
        status='accepted',
        is_fake=True
    )

    count_fakes = fake_apps.count()
    if count_fakes == 0:
        return 0

    for fake in fake_apps:
        fake.status = 'rejected'
        fake.save()

    replacements = (
        Application.objects
        .filter(offer_id=offer_id, status='pending', is_fake=False)
        .order_by('-predicted_fit')[:count_fakes]
    )

    for app in replacements:
        app.status = 'accepted'
        app.save()

    return count_fakes


@api_view(["POST"])
@permission_classes([IsAuthenticated])  
def replace_fakes_api(request, offer_id):
    # Role check
    # if getattr(request.user.profile, "role", "student") not in ("recruiter", "admin"):
    #     return Response({"detail": "Forbidden"}, status=403)
    count = replace_fake_candidates(offer_id)
    return Response({"message": f"{count} fake candidates replaced."})



class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.select_related('application', 'recruiter').all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]  


class OfferViewSet(viewsets.ModelViewSet):
    queryset = Offer.objects.prefetch_related('required_skills').all()
    serializer_class = OfferSerializer
    permission_classes = [IsAuthenticated] 
    def create(self, request, *args, **kwargs):
        user = request.user
        profile = user.profile

        if profile.role != "recruiter":
            return Response({"error": "Only recruiters can create offers."}, status=403)

        if not profile.company:
            return Response({"error": "Recruiter must belong to a company."}, status=400)

        data = request.data

        title = data.get("title")
        description = data.get("description", "")
        field_required = data.get("field_required")
        level_required = data.get("level_required", "intern")
        skills_list = data.get("required_skills", [])  

        if not title or not field_required:
            return Response({"error": "title and field_required are required"}, status=400)

        offer = Offer.objects.create(
            title=title,
            description=description,
            field_required=field_required,
            level_required=level_required,
            company=profile.company,  
            created_by=user
        )

        skills = []
        for name in skills_list:
            skill, _ = Skill.objects.get_or_create(name=name)
            skills.append(skill)

        offer.required_skills.set(skills)

        return Response({
            "message": "Offer created",
            "id": offer.id,
            "title": offer.title,
            "company": profile.company.name,
            "skills": [s.name for s in skills]
        }, status=201)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_company(self, request):
        profile = request.user.profile

        if profile.role != "recruiter":
            return Response({"detail": "Only recruiters can access this."}, status=403)

        if not profile.company:
            return Response({"detail": "You are not assigned to any company."}, status=400)

        offers = Offer.objects.filter(company=profile.company)

        serializer = OfferSerializer(offers, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def recommended(self, request):

        user = request.user
        profile = getattr(user, "profile", None)

        if not profile or profile.role != "student":
            return Response({"detail": "Only students can view recommendations."}, status=403)

        today = date.today()
        applied_offer_ids = Application.objects.filter(user=user).values_list("offer_id", flat=True)

        offers = Offer.objects.filter(is_closed=False).exclude(id__in=applied_offer_ids)

        results = []
        for offer in offers:
            if offer.deadline and today > offer.deadline:
                if not (offer.extended_deadline and today <= offer.extended_deadline):
                    continue
            serialized_offer = OfferSerializer(offer).data  
            fit = predict_fit(profile, offer)
            results.append({
                "offer": serialized_offer,
                "predicted_fit": round(fit, 3),
            })

        results.sort(key=lambda x: x["predicted_fit"], reverse=True)

        return Response({
            "student": user.email,
            "total_offers": len(results),
            "offers": results
        })
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def close(self, request, pk=None):
        offer = self.get_object()
        offer.is_closed = True
        offer.closed_at = timezone.now()
        offer.save()

        applications = Application.objects.filter(offer=offer).order_by('-predicted_fit')[:10]
        rank_to_points = {1: 15, 2: 13, 3: 11, 4: 9, 5: 7, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1}

        for rank, app in enumerate(applications, start=1):
            if app.status != 'accepted' and not app.is_fake:
                bonus_points = rank_to_points.get(rank, 0)
                profile = app.user.profile
                profile.score += bonus_points
                profile.save()

                ScoreHistory.objects.create(
                    user=app.user,
                    reason=f"Top {rank} in offer {offer.title} (Bonus)",
                    points=bonus_points
                )

        return Response({"message": f"Offer {offer.title} closed and bonus distributed."}, status=200)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reopen(self, request, pk=None):
        offer = self.get_object()
        offer.is_closed = False
        offer.closed_at = None
        offer.save()
        return Response({"message": f"Offer {offer.title} reopened."}, status=200)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def extend_deadline(self, request, pk=None):
        offer = self.get_object()
        new_deadline = request.data.get('extended_deadline')
        if not new_deadline:
            return Response({"error": "extended_deadline is required"}, status=400)
        try:
            offer.extended_deadline = datetime.strptime(new_deadline, "%Y-%m-%d").date()
            offer.save()
            return Response({"message": f"Offer deadline extended to {new_deadline}"})
        except Exception:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)



class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]


class CertificationViewSet(viewsets.ModelViewSet):
    queryset = Certification.objects.all()
    serializer_class = CertificationSerializer
    permission_classes = [IsAuthenticated]



class ScoreHistoryViewSet(viewsets.ModelViewSet):
    queryset = ScoreHistory.objects.all()
    serializer_class = ScoreHistorySerializer
    permission_classes = [IsAuthenticated]



from rest_framework import generics
from rest_framework_simplejwt.tokens import RefreshToken

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = serializer.save()

        return Response(payload, status=status.HTTP_201_CREATED)
@method_decorator(csrf_exempt, name='dispatch')
class EmailTokenObtainPairView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
@api_view(["POST"])
@permission_classes([IsAdminUser])
def approve_user(request, user_id):
    try:
        profile = Profile.objects.get(user__id=user_id)
        profile.is_verified = True
        profile.save()
        return Response({"message": f"✅ {profile.user.email} has been approved."})
    except Profile.DoesNotExist:
        return Response({"error": "Profile not found."}, status=404)

@api_view(["GET"])
@permission_classes([IsAdminUser])
def pending_users(request):
    pending = Profile.objects.filter(is_verified=False)
    data = [
        {
            "id": p.user.id,
            "email": p.user.email,
            "role": p.role,
            "created": p.user.date_joined
        } for p in pending
    ]
    return Response(data)

def html_jwt_login(request):
    return render(request, "api/login.html")

def html_register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful! You can now log in.")
            return redirect("html_login")
    else:
        form = RegisterForm()
    return render(request, "api/register.html", {"form": form})


def html_logout(request):
    logout(request)
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect("html_login")

class HomeView(TemplateView):
    template_name = "api/home.html"
def html_jwt_login(request):
    return render(request, "api/login.html")

def html_jwt_register(request):
    return render(request, "api/register.html")
class UniversityViewSet(viewsets.ModelViewSet):
    queryset = University.objects.all()
    serializer_class = UniversitySerializer
    permission_classes = [permissions.AllowAny]

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.AllowAny]

class InternshipDemandViewSet(viewsets.ModelViewSet):
    queryset = InternshipDemand.objects.select_related("student", "application", "university")
    serializer_class = InternshipDemandSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def accepted(self, request):
        user = request.user
        apps = Application.objects.filter(user=user, status="accepted")
        serializer = ApplicationSerializer(apps, many=True)
        return Response(serializer.data)
    def create(self, request, *args, **kwargs):
        user = request.user
        profile = user.profile

        if profile.role != "student":
            return Response({"error": "Only students can submit internship demands."}, status=403)

        application_id = request.data.get("application_id")
        if not application_id:
            return Response({"error": "application_id is required"}, status=400)

        try:
            app = Application.objects.get(id=application_id, user=user, status="accepted")
        except Application.DoesNotExist:
            return Response({"error": "Valid accepted application not found"}, status=404)

        if hasattr(app, "internship_demand"):
            return Response({"error": "Demand already exists for this application"}, status=400)

        if not profile.university:
            return Response({"error": "Student is not assigned to a university."}, status=400)

        demand = InternshipDemand.objects.create(
            student=user,
            application=app,
            university=profile.university
        )

        serializer = self.get_serializer(demand)
        return Response(serializer.data, status=201)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_demands(self, request):
        """ Student → list all internship demands """
        user = request.user
        demands = InternshipDemand.objects.filter(student=user)
        serializer = self.get_serializer(demands, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def university_demands(self, request):
        """ University → list all demands from students belonging to that university """
        profile = request.user.profile

        if profile.role != "university":
            return Response({"error": "Only university users can access this."}, status=403)

        if not profile.university:
            return Response({"error": "University not found for this user"}, status=400)

        demands = InternshipDemand.objects.filter(university=profile.university)
        serializer = self.get_serializer(demands, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        profile = request.user.profile
        if profile.role != "university":
            return Response({"error": "Only university can approve demands."}, status=403)

        demand = self.get_object()
        demand.status = "approved"
        demand.reviewed_at = timezone.now()
        demand.save()

        return Response({"message": "Demand approved. Student can now request documents."})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        profile = request.user.profile

        if profile.role != "university":
            return Response({"error": "Only university users can reject demands."}, status=403)

        demand = self.get_object()
        demand.status = "rejected"
        demand.reviewed_at = timezone.now()
        demand.save()

        return Response({"message": "Internship demand rejected."})

    @action(detail=False, methods=['get'], url_path="student/(?P<student_id>[^/.]+)/details")
    def student_details(self, request, student_id=None):
        # only university can access
        profile = request.user.profile
        if profile.role != "university":
            return Response({"error": "Only university users can access this."}, status=403)

        # get student
        try:
            student_user = User.objects.get(id=student_id)
        except User.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        # only show if student belongs to this university
        if student_user.profile.university != profile.university:
            return Response({"error": "This student does not belong to your university"}, status=403)

        # accepted applications
        apps = Application.objects.filter(user=student_user, status="accepted")

        apps_serialized = []
        for app in apps:
            apps_serialized.append({
                "id": app.id,
                "offer_title": app.offer.title,
                "company": app.offer.company.name,
                "field_required": app.offer.field_required,
                "level_required": app.offer.level_required,
                "predicted_fit": app.predicted_fit,
            })

        # demand (if exists)
        demand = InternshipDemand.objects.filter(student=student_user).first()
        demand_data = None
        if demand:
            demand_data = {
                "id": demand.id,
                "status": demand.status,
                "created_at": demand.created_at,
                "reviewed_at": demand.reviewed_at,
            }

        return Response({
            "student": {
                "id": student_user.id,
                "email": student_user.email,
                "field_of_study": student_user.profile.field_of_study,
                "gpa": student_user.profile.gpa,
                "score": student_user.profile.score
            },
            "accepted_applications": apps_serialized,
            "internship_demand": demand_data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_convention(self, request, pk=None):
        demand = self.get_object()

        # Ensure ONLY the student can generate his own papers
        if request.user != demand.student:
            return Response({"error": "You can generate only your own internship documents."}, status=403)

        # Check if demand was accepted by university
        if demand.status != "approved":
            return Response({"error": "University has not approved this internship yet."}, status=400)

        # PDF generation logic (same as before)
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from django.core.mail import EmailMessage
        from io import BytesIO

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        p.setFont("Helvetica", 16)
        p.drawString(50, 800, "Convention de Stage")

        p.setFont("Helvetica", 12)
        p.drawString(50, 760, f"Université : {demand.university.name}")
        p.drawString(50, 740, f"Étudiant : {demand.student.email}")
        p.drawString(50, 720, f"Entreprise : {demand.application.offer.company.name}")
        p.drawString(50, 700, f"Offre : {demand.application.offer.title}")

        p.drawString(50, 660, "Ce document confirme le stage de l'étudiant au sein de l'entreprise.")
        p.drawString(50, 640, "Signature Université: _____________________")
        p.drawString(50, 620, "Signature Entreprise: _____________________")
        p.drawString(50, 600, "Signature Étudiant: _______________________")

        p.showPage()
        p.save()

        buffer.seek(0)
        pdf_data = buffer.getvalue()

        # Send by email
        email = EmailMessage(
            subject="Convention de Stage",
            body="Veuillez trouver ci-joint votre convention de stage.",
            to=[request.user.email]
        )
        email.attach("Convention_de_Stage.pdf", pdf_data, "application/pdf")
        email.send()

        return Response({"message": "Convention sent by email."})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_letter(self, request, pk=None):
        demand = self.get_object()

        if request.user != demand.student:
            return Response({"error": "You can generate only your own internship documents."}, status=403)

        if demand.status != "approved":
            return Response({"error": "University has not approved this internship yet."}, status=400)

        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from django.core.mail import EmailMessage
        from io import BytesIO

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        p.setFont("Helvetica", 16)
        p.drawString(50, 800, "Lettre d'Affectation")

        p.setFont("Helvetica", 12)
        p.drawString(50, 760, f"Université : {demand.university.name}")
        p.drawString(50, 740, f"Étudiant : {demand.student.email}")
        p.drawString(50, 720, f"Affectation : {demand.application.offer.company.name}")

        p.drawString(50, 700, "L'étudiant est affecté officiellement à l'entreprise susmentionnée.")
        p.drawString(50, 680, "Signature de l'Université : ____________________")

        p.showPage()
        p.save()

        buffer.seek(0)
        pdf_data = buffer.getvalue()

        email = EmailMessage(
            subject="Lettre d'Affectation",
            body="Veuillez trouver ci-joint votre lettre d’affectation.",
            to=[request.user.email]
        )
        email.attach("Lettre_Affectation.pdf", pdf_data, "application/pdf")
        email.send()

        return Response({"message": "Lettre d'affectation sent by email."})

