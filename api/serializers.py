from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Application, Offer, Profile, Skill, Certification, University, ScoreHistory, Feedback, Company, \
    InternshipDemand

User = get_user_model()


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


class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    role = serializers.CharField(read_only=True)
    university = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    skills = SkillSerializer(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "role",
            "field_of_study",
            "gpa",
            "score",
            "university",
            "company",
            "skills",
            "certifications",
        ]

    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "email": obj.user.email,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name
        }

    def get_university(self, obj):
        if not obj.university:
            return None
        return {
            "id": obj.university.id,
            "name": obj.university.name,
            "city": obj.university.city,
            "country": obj.university.country,
        }

    def get_company(self, obj):
        if not obj.company:
            return None
        return {
            "id": obj.company.id,
            "name": obj.company.name,
            "industry": obj.company.industry,
            "city": obj.company.city,
            "country": obj.company.country,
        }

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class OfferSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)  
    required_skills = SkillSerializer(many=True, read_only=True)

    skills = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Offer
        fields = [
            "id", "title", "description", "company",
            "field_required", "level_required",
            "location", "deadline", "is_closed",
            "required_skills", "skills"
        ]

    def create(self, validated_data):
        skills_list = validated_data.pop("skills", [])
        offer = Offer.objects.create(**validated_data)

        for s in skills_list:
            skill, _ = Skill.objects.get_or_create(name=s.lower())
            offer.required_skills.add(skill)

        return offer


# ✅ APPLICATION (already exists)
class ApplicationSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    offer = OfferSerializer(read_only=True)

    class Meta:
        model = Application
        fields = ["id", "user", "offer", "status", "predicted_fit"]

    def get_user(self, obj):
        profile = getattr(obj.user, "profile", None)
        data = {
            "id": obj.user.id,
            "email": obj.user.email,
        }
        if profile:
            data.update({
                "field_of_study": profile.field_of_study,
                "gpa": profile.gpa,
                "score": profile.score
            })
        return data



class ScoreHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreHistory
        fields = ["id", "user", "reason", "points", "created_at"]
class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Profile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=Profile.ROLE_CHOICES, default="student")

    # Student-only
    field_of_study = serializers.CharField(required=False, allow_blank=True)
    gpa = serializers.DecimalField(required=False, allow_null=True, max_digits=4, decimal_places=2)

    # University relation (select existing OR create new—only for uni admins)
    university_id = serializers.IntegerField(required=False)
    university_name = serializers.CharField(required=False, allow_blank=True)
    university_city = serializers.CharField(required=False, allow_blank=True)
    university_country = serializers.CharField(required=False, allow_blank=True)
    university_website = serializers.URLField(required=False, allow_blank=True)

    # Company relation (select existing OR create new—only for recruiters)
    company_id = serializers.IntegerField(required=False)
    company_name = serializers.CharField(required=False, allow_blank=True)
    company_industry = serializers.CharField(required=False, allow_blank=True)
    company_city = serializers.CharField(required=False, allow_blank=True)
    company_country = serializers.CharField(required=False, allow_blank=True)
    company_website = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "email", "password", "first_name", "last_name", "role",
            "field_of_study", "gpa",
            "university_id", "university_name", "university_city", "university_country", "university_website",
            "company_id", "company_name", "company_industry", "company_city", "company_country", "company_website",
        ]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        role = attrs.get("role", "student")

        # Student: MUST choose existing university (by id). No creation allowed.
        if role == "student":
            if not attrs.get("university_id"):
                raise serializers.ValidationError({"university_id": "Student must select an existing university."})
            # Ensure no creation payload sneaks in
            for f in ("university_name", "university_city", "university_country", "university_website"):
                if attrs.get(f):
                    raise serializers.ValidationError(
                        {"university": "Students cannot create universities; select an existing one."}
                    )

        # University admin: either pick existing (id) OR create (name required)
        if role == "university":
            uni_id = attrs.get("university_id")
            uni_name = attrs.get("university_name")
            if not uni_id and not uni_name:
                raise serializers.ValidationError(
                    {"university": "Provide either university_id (existing) or university_name (to create)."}
                )

        # Recruiter: either pick existing (id) OR create (name required)
        if role == "recruiter":
            comp_id = attrs.get("company_id")
            comp_name = attrs.get("company_name")
            if not comp_id and not comp_name:
                raise serializers.ValidationError(
                    {"company": "Provide either company_id (existing) or company_name (to create)."}
                )

        return attrs

    def create(self, validated_data):
        role = validated_data.pop("role", "student")

        # Extract relation fields before creating user
        uni_id = validated_data.pop("university_id", None)
        uni_name = validated_data.pop("university_name", "").strip()
        uni_city = validated_data.pop("university_city", "").strip()
        uni_country = validated_data.pop("university_country", "").strip()
        uni_website = validated_data.pop("university_website", "").strip()

        comp_id = validated_data.pop("company_id", None)
        comp_name = validated_data.pop("company_name", "").strip()
        comp_industry = validated_data.pop("company_industry", "").strip()
        comp_city = validated_data.pop("company_city", "").strip()
        comp_country = validated_data.pop("company_country", "").strip()
        comp_website = validated_data.pop("company_website", "").strip()

        field_of_study = validated_data.pop("field_of_study", "").strip()
        gpa = validated_data.pop("gpa", None)

        # Create user
        user = User.objects.create_user(
            email=validated_data.get("email"),
            password=validated_data.get("password"),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", "")
        )

        # Create profile
        profile = Profile.objects.create(user=user, role=role)

        # Link/create entities per role
        if role == "student":
            # Existing university only
            try:
                university = University.objects.get(id=uni_id)
            except University.DoesNotExist:
                raise serializers.ValidationError({"university_id": "Invalid university ID"})
            profile.university = university
            profile.field_of_study = field_of_study
            profile.gpa = gpa
            profile.is_verified = True  # students auto-verified

        elif role == "university":
            # Either link existing OR create new university
            if uni_id:
                try:
                    university = University.objects.get(id=uni_id)
                except University.DoesNotExist:
                    raise serializers.ValidationError({"university_id": "Invalid university ID"})
            else:
                if not uni_name:
                    raise serializers.ValidationError({"university_name": "University name is required to create."})
                university, _ = University.objects.get_or_create(
                    name=uni_name,
                    defaults={
                        "city": uni_city,
                        "country": uni_country,
                        "website": uni_website,
                    }
                )
            profile.university = university
            profile.is_verified = False  # pending admin approval (your policy)

        elif role == "recruiter":
            # Either link existing OR create new company
            if comp_id:
                try:
                    company = Company.objects.get(id=comp_id)
                except Company.DoesNotExist:
                    raise serializers.ValidationError({"company_id": "Invalid company ID"})
            else:
                if not comp_name:
                    raise serializers.ValidationError({"company_name": "Company name is required to create."})
                company, _ = Company.objects.get_or_create(
                    name=comp_name,
                    defaults={
                        "industry": comp_industry,
                        "city": comp_city,
                        "country": comp_country,
                        "website": comp_website,
                    }
                )
            profile.company = company
            profile.is_verified = False  # pending admin approval (your policy)

        profile.save()

        # Return tokens (+ user info)
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": profile.role,
                "university": profile.university.name if profile.university else None,
                "company": profile.company.name if profile.company else None,
            },
        }


class EmailTokenObtainPairSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        # ✅ Handle duplicates gracefully
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError({"detail": "No user with this email."})

        # ✅ Authenticate using username under the hood
        user = authenticate(email=user.email, password=password)
        if not user:
            raise serializers.ValidationError({"detail": "Invalid credentials."})

        # ✅ Check verification status
        profile = getattr(user, "profile", None)
        if profile:
            # If recruiter/university and not verified → block login
            if profile.role in ["recruiter", "university"] and not profile.is_verified:
                raise serializers.ValidationError(
                    {"detail": "Your account is pending admin approval. Please wait until it's verified."}
                )

        # ✅ Generate tokens manually
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": profile.role if profile else None,
                "is_verified": profile.is_verified if profile else None,
            }
        }
class InternshipDemandSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternshipDemand
        fields = "__all__"
        read_only_fields = ["student", "university", "status", "created_at", "reviewed_at"]
