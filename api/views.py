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
    University, ScoreHistory, Feedback
)
from api.serializers import (
    ApplicationSerializer, ProfileSerializer, OfferSerializer,
    SkillSerializer, CertificationSerializer, UniversitySerializer,
    ScoreHistorySerializer, FeedbackSerializer, RegisterSerializer, EmailTokenObtainPairSerializer
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
            "message": f"Candidate {app.user.username} marked as fake.",
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
            "user": user.username,
            "offer": offer.title,
            "predicted_fit": round(fit_score, 3),
            "id": app.id
        }, status=201 if created else 200)


# =========================
# 👤 PROFILES
# =========================
class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user').prefetch_related('skills', 'certifications')
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]  # 🔒 secure

    def create(self, request, *args, **kwargs):
        """
        Hardened: create/update ONLY the authenticated user's profile.
        """
        user = request.user
        data = request.data

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.field_of_study = data.get("field_of_study", profile.field_of_study or "")
        profile.gpa = data.get("gpa", profile.gpa or 0)
        profile.score = data.get("score", profile.score or 0)
        profile.role = data.get("role", profile.role or "student")
        profile.save()

        skill_names = data.get("skills", [])
        cert_names = data.get("certifications", [])

        skills = [Skill.objects.get_or_create(name=name)[0] for name in skill_names]
        certs = [Certification.objects.get_or_create(name=name)[0] for name in cert_names]
        profile.skills.set(skills)
        profile.certifications.set(certs)
        profile.save()

        return Response({
            "message": "Profile created/updated",
            "id": profile.id,
            "user": user.username,
            "role": profile.role,
            "skills": [s.name for s in skills],
            "certifications": [c.name for c in certs],
        })


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
            "username": a.user.username,
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
@permission_classes([IsAuthenticated])  # 🔒 secure
def replace_fakes_api(request, offer_id):
    # Role check
    # if getattr(request.user.profile, "role", "student") not in ("recruiter", "admin"):
    #     return Response({"detail": "Forbidden"}, status=403)
    count = replace_fake_candidates(offer_id)
    return Response({"message": f"{count} fake candidates replaced."})



class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.select_related('application', 'recruiter').all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]  # 🔒 secure



class OfferViewSet(viewsets.ModelViewSet):
    queryset = Offer.objects.prefetch_related('required_skills').all()
    serializer_class = OfferSerializer
    permission_classes = [IsAuthenticated]  # 🔒 secure

    def create(self, request, *args, **kwargs):
        data = request.data
        title = data.get("title")
        company = data.get("company", "Unknown")
        field = data.get("field_required")
        level = data.get("level_required", "intern")
        skill_names = data.get("required_skills", [])

        if not title or not field:
            return Response({"error": "title and field_required required"}, status=400)

        # Role check
        # if getattr(request.user.profile, "role", "student") not in ("recruiter", "admin"):
        #     return Response({"detail": "Forbidden"}, status=403)

        created_by = request.user  # 🔒 use the authenticated user

        offer = Offer.objects.create(
            title=title,
            company=company,
            field_required=field,
            level_required=level,
            created_by=created_by,
        )

        skills = [Skill.objects.get_or_create(name=name)[0] for name in skill_names]
        offer.required_skills.set(skills)

        return Response({
            "message": "Offer created",
            "id": offer.id,
            "title": offer.title,
            "recruiter": created_by.username if created_by else None,
            "skills": [s.name for s in skills],
            "field_required": field
        }, status=201)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def close(self, request, pk=None):
        # (Optionally: restrict to offer owner or recruiter/admin)
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


class UniversityViewSet(viewsets.ModelViewSet):
    queryset = University.objects.all()
    serializer_class = UniversitySerializer
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
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=201)
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
