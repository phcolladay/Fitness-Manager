from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Email or username", max_length=254)


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    sex = forms.ChoiceField(
        choices=[("", "---------"), ("male", "Male"), ("female", "Female"), ("other", "Other")], required=False
    )
    age_years = forms.IntegerField(min_value=0, required=False)
    height_cm = forms.DecimalField(min_value=0, max_digits=5, decimal_places=2, required=False)
    weight_kg = forms.DecimalField(min_value=0, max_digits=5, decimal_places=2, required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

