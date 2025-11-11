from django import forms
from django.contrib.auth import authenticate, get_user_model
from api.models import Profile, University

User = get_user_model()

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def clean(self):
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")
        user = User.objects.filter(email=email).first()

        if not user:
            raise forms.ValidationError("Invalid email or password.")
        if not user.check_password(password):
            raise forms.ValidationError("Invalid email or password.")
        self.cleaned_data["user"] = user
        return self.cleaned_data


# api/forms.py
class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))

    # Role-specific fields
    university_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    company_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    field_of_study = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    gpa = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "password", "role"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.save()

        role = self.cleaned_data["role"]
        profile = Profile.objects.create(user=user, role=role)

        if role == "university":
            uni_name = self.cleaned_data.get("university_name")
            if uni_name:
                uni, _ = University.objects.get_or_create(name=uni_name)
                profile.university = uni

        elif role == "recruiter":
            profile.notes = f"Company: {self.cleaned_data.get('company_name')}"

        elif role == "student":
            profile.field_of_study = self.cleaned_data.get("field_of_study", "")
            profile.gpa = self.cleaned_data.get("gpa")

        profile.is_verified = True if role == "student" else False
        profile.save()
        return user
