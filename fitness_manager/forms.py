import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Email or username", max_length=254)


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    username = forms.CharField(
        label="Username",
        required=False,
        help_text="Optional. Leave blank to use your email prefix.",
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    sex = forms.ChoiceField(
        choices=[
            ("", "---------"),
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        required=False,
    )
    age_years = forms.IntegerField(min_value=0, required=False)
    height_cm = forms.DecimalField(min_value=0, max_digits=5, decimal_places=2, required=False)
    weight_kg = forms.DecimalField(min_value=0, max_digits=5, decimal_places=2, required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("email", "username")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            return ""

        User = get_user_model()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("An account with this username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        username = (cleaned_data.get("username") or "").strip()
        if email and not username:
            cleaned_data["username"] = self._generate_unique_username(email)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["username"]
        if commit:
            user.save()
        return user

    @staticmethod
    def _generate_unique_username(email: str) -> str:
        User = get_user_model()
        max_length = User._meta.get_field("username").max_length or 150
        local_part = (email.split("@", 1)[0] or "user").lower()
        base = re.sub(r"[^a-z0-9_.+-]+", "_", local_part).strip("._+-") or "user"
        base = base[:max_length]

        for suffix_number in range(0, 10_000):
            suffix = "" if suffix_number == 0 else str(suffix_number)
            candidate = f"{base[: max_length - len(suffix)]}{suffix}"
            if not User.objects.filter(username__iexact=candidate).exists():
                return candidate

        fallback_base = "user"
        for suffix_number in range(10_000, 100_000):
            candidate = f"{fallback_base}{suffix_number}"[:max_length]
            if not User.objects.filter(username__iexact=candidate).exists():
                return candidate

        raise forms.ValidationError("Unable to generate a unique username. Please enter a username.")

