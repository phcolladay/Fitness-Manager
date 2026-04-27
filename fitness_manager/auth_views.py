import logging
import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.views import PasswordResetView
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.profiles.models import UserProfile
from .forms import SignupForm
from .showcase_data import seed_showcase_data

logger = logging.getLogger(__name__)


def _cleanup_stale_guest_users(max_age_hours: int = 24) -> None:
    """
    Best-effort cleanup for abandoned guest users/data.
    """
    User = get_user_model()
    cutoff = timezone.now() - timedelta(hours=max_age_hours)
    username_field = getattr(User, "USERNAME_FIELD", "username")
    filters = {
        f"{username_field}__startswith": "guest_",
        "is_superuser": False,
        "is_staff": False,
        "date_joined__lt": cutoff,
    }
    User.objects.filter(**filters).delete()


def signup(request):
    if request.user.is_authenticated:
        return redirect("workouts:home")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.sex = form.cleaned_data.get("sex", "")
                profile.age_years = form.cleaned_data.get("age_years")
                profile.height_cm = form.cleaned_data.get("height_cm")
                profile.weight_kg = form.cleaned_data.get("weight_kg")
                profile.save()
            # Multiple auth backends are configured; set backend explicitly for session login.
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("workouts:home")
        messages.error(request, "Sign up failed. Please review the errors below (password rules apply).")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})


class ResilientPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    html_email_template_name = "registration/password_reset_email.html"
    success_url = reverse_lazy("password_reset_done")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception:  # noqa: BLE001
            logger.exception("Password reset email delivery failed.")
            messages.error(
                self.request,
                "We couldn't send the reset email right now. Please try again later.",
            )
            return self.render_to_response(self.get_context_data(form=form))


@require_POST
def guest_login(request):
    """
    Creates a temporary user and logs them in.

    This keeps all existing @login_required views working and preserves per-user data isolation,
    while avoiding a registration step for "try it now" visitors.
    """
    if request.user.is_authenticated:
        return redirect("workouts:home")

    _cleanup_stale_guest_users()

    User = get_user_model()
    username_field = getattr(User, "USERNAME_FIELD", "username")

    for _ in range(20):
        ident = secrets.token_hex(4)
        value = f"guest_{ident}"
        if username_field == "email":
            value = f"guest_{ident}@guest.local"
        if not User.objects.filter(**{username_field: value}).exists():
            user = User(**{username_field: value})
            # Guests shouldn't have a reusable password.
            if hasattr(user, "set_unusable_password"):
                user.set_unusable_password()
            user.save()
            seed_showcase_data(user)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            request.session.set_expiry(0)  # expire on browser close
            request.session["guest_showcase_data_ready"] = True
            messages.info(
                request,
                "You are using a guest account with sample data. Create an account to keep your own data long-term.",
            )
            break
    else:
        messages.error(request, "Guest login is temporarily unavailable. Please try again.")
        return redirect("login")

    next_url = request.POST.get("next") or ""
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("workouts:home")


def logout_view(request):
    if request.method != "POST":
        return redirect("login")
    user = request.user if request.user.is_authenticated else None
    username_field = getattr(get_user_model(), "USERNAME_FIELD", "username")
    user_identifier = getattr(user, username_field, "") if user else ""
    is_guest = bool(user_identifier and str(user_identifier).startswith("guest_"))
    logout(request)
    if is_guest and user:
        user.delete()
    return redirect("login")
