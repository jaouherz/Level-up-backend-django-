from django import forms
from api.models import Offer, Feedback, Application

class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = [
            "title", "company", "description", "field_required",
            "level_required", "required_skills", "location",
            "deadline", "extended_deadline", "is_closed"
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "required_skills": forms.SelectMultiple(attrs={"size": 6}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "extended_deadline": forms.DateInput(attrs={"type": "date"}),
        }

class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["status"]
        widgets = {
            "status": forms.Select()
        }

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["feedback_type", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional notes…"})
        }
