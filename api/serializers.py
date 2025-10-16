from rest_framework import serializers
from .models import Application, Offer, Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["id", "user", "field_of_study", "gpa", "score"]


class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = ["id", "title", "field_required"]


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