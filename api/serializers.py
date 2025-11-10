from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Application, Offer, Profile, Skill, Certification, University, ScoreHistory, Feedback


# ✅ SKILL
class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]


# ✅ CERTIFICATION
class CertificationSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(),
        many=True,
        write_only=True,
        source='skills'
    )

    class Meta:
        model = Certification
        fields = ["id", "name", "issuer", "issued_at", "level", "skills", "skill_ids"]


# ✅ UNIVERSITY
class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ["id", "name", "city", "country", "website", "email_domain"]


# ✅ PROFILE (already exists, now extended)
class ProfileSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    skill_ids = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(),
        many=True,
        write_only=True,
        source='skills'
    )
    cert_ids = serializers.PrimaryKeyRelatedField(
        queryset=Certification.objects.all(),
        many=True,
        write_only=True,
        source='certifications'
    )

    class Meta:
        model = Profile
        fields = ["id", "user", "field_of_study", "gpa", "score", "skills", "certifications", "skill_ids", "cert_ids"]


# ✅ OFFER (already exists — optional to extend)
class OfferSerializer(serializers.ModelSerializer):
    required_skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(),
        many=True,
        write_only=True,
        source='required_skills'
    )

    class Meta:
        model = Offer
        fields = ["id", "title", "company", "field_required", "description", "location", "required_skills", "skill_ids"]


# ✅ APPLICATION (already exists)
class ApplicationSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    offer = OfferSerializer(read_only=True)

    class Meta:
        model = Application
        fields = ["id", "user", "offer", "status", "predicted_fit"]


    def get_user(self, obj):
        profile = getattr(obj.user, "profile", None)
        if profile:
            return {
                "id": obj.user.id,
                "username": obj.user.username,
                "field_of_study": profile.field_of_study,
                "gpa": profile.gpa,
                "score": profile.score
            }
        return {"id": obj.user.id, "username": obj.user.username}



class ScoreHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreHistory
        fields = ["id", "user", "reason", "points", "created_at"]
class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Profile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        # ✅ DO NOT manually create a Profile here
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", "")
        )
        return user
User = get_user_model()

class EmailTokenObtainPairSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        # ✅ handle duplicates gracefully
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError({"detail": "No user with this email."})

        # ✅ authenticate using username under the hood
        user = authenticate(username=user.username, password=password)
        if not user:
            raise serializers.ValidationError({"detail": "Invalid credentials."})

        # ✅ generate tokens manually
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        }