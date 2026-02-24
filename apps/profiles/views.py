from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BodyMeasurementForm, UserProfileForm
from .models import BodyMeasurement, UserProfile


def _profile_for(user) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@login_required
def profile_edit(request):
    profile = _profile_for(request.user)
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profiles:profile")
    else:
        form = UserProfileForm(instance=profile)

    return render(
        request,
        "profiles/profile.html",
        {
            "form": form,
            "profile": profile,
            "recommended_calories": profile.estimated_daily_calories(),
        },
    )


@login_required
def body_metrics_list(request):
    entries = BodyMeasurement.objects.filter(user=request.user).order_by("-measured_on", "-id")
    today = timezone.localdate()
    seven_days_ago = today - timedelta(days=6)
    month_ago = today - timedelta(days=29)

    summaries = {
        "daily": entries.filter(measured_on=today).aggregate(avg=Avg("weight_kg"))["avg"],
        "weekly": entries.filter(measured_on__gte=seven_days_ago).aggregate(avg=Avg("weight_kg"))["avg"],
        "monthly": entries.filter(measured_on__gte=month_ago).aggregate(avg=Avg("weight_kg"))["avg"],
    }
    latest = entries.first()
    trend = None
    if latest and entries.count() > 1:
        previous = entries[1]
        trend = float(latest.weight_kg - previous.weight_kg)

    return render(
        request,
        "profiles/body_metrics_list.html",
        {"entries": entries, "summaries": summaries, "trend": trend},
    )


@login_required
def body_metric_add(request):
    if request.method == "POST":
        form = BodyMeasurementForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            messages.success(request, "Body measurement saved.")
            return redirect("profiles:body_metrics")
    else:
        form = BodyMeasurementForm()
    return render(request, "profiles/body_metric_form.html", {"form": form, "mode": "add"})


@login_required
def body_metric_edit(request, entry_id: int):
    entry = get_object_or_404(BodyMeasurement, id=entry_id, user=request.user)
    if request.method == "POST":
        form = BodyMeasurementForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, "Body measurement updated.")
            return redirect("profiles:body_metrics")
    else:
        form = BodyMeasurementForm(instance=entry)
    return render(request, "profiles/body_metric_form.html", {"form": form, "mode": "edit"})


@login_required
def body_metric_delete(request, entry_id: int):
    entry = get_object_or_404(BodyMeasurement, id=entry_id, user=request.user)
    if request.method == "POST":
        entry.delete()
        messages.success(request, "Body measurement deleted.")
    return redirect("profiles:body_metrics")

# Create your views here.
