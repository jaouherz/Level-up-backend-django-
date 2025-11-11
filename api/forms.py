from django import forms
from django.contrib.auth import authenticate, get_user_model
from api.models import Profile

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


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "password"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.save()
        Profile.objects.create(user=user, role="student", is_verified=True)
        return user
