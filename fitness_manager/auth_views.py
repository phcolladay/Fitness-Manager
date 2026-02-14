import secrets

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


def signup(request):
    if request.user.is_authenticated:
        return redirect("workouts:home")
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("workouts:home")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


@require_POST
def guest_login(request):
    """
    Creates a temporary user and logs them in.

    This keeps all existing @login_required views working and preserves per-user data isolation,
    while avoiding a registration step for "try it now" visitors.
    """
    if request.user.is_authenticated:
        return redirect("workouts:home")

    User = get_user_model()
    username_field = getattr(User, "USERNAME_FIELD", "username")

    for _ in range(20):
        ident = secrets.token_hex(4)
        value = f"guest_{ident}"
        if not User.objects.filter(**{username_field: value}).exists():
            user = User(**{username_field: value})
            # Guests shouldn't have a reusable password.
            if hasattr(user, "set_unusable_password"):
                user.set_unusable_password()
            user.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            request.session.set_expiry(0)  # expire on browser close
            messages.info(request, "You are using a guest account. Create an account to keep your data long-term.")
            break
    else:
        messages.error(request, "Guest login is temporarily unavailable. Please try again.")
        return redirect("login")

    next_url = request.POST.get("next") or ""
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("workouts:home")
