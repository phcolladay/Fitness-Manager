import logging
import os
import json
from urllib.parse import urlencode
from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.profiles.models import UserProfile
from apps.workouts.models import ExerciseEntry

from .forms import FoodEntryForm, FoodEstimateForm, FoodLookupForm, FoodPhotoForm, WaterEntryForm
from .models import FoodEntry, FoodPhoto, WaterEntry
from .services import search_usda_foods
from .vision import estimate_food_from_text, recognize_food

logger = logging.getLogger(__name__)


def _period_range(period: str):
    today = timezone.localdate()
    if period == "week":
        start = today - timedelta(days=6)
    elif period == "month":
        start = today - timedelta(days=29)
    else:
        period = "day"
        start = today
    start_dt = timezone.make_aware(datetime.combine(start, time.min))
    end_dt = timezone.make_aware(datetime.combine(today, time.max))
    return period, start, today, start_dt, end_dt


def _normalize_micronutrients(raw: object) -> dict[str, float]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    if not isinstance(raw, dict):
        return {}
    normalized = {}
    for key, value in raw.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric < 0:
            continue
        normalized[str(key)] = numeric
    return normalized


def _prefill_add_url(*, source: str, result: dict, default_name: str) -> str:
    micronutrients = _normalize_micronutrients(result.get("micronutrients"))
    for key in ("fiber_g", "sodium_mg", "iron_mg", "calcium_mg", "vitamin_c_mg", "potassium_mg"):
        value = result.get(key)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric < 0:
            continue
        micronutrients[key] = numeric

    params = {
        "source": source,
        "name": result.get("name", default_name),
        "brand": result.get("brand", "") or "",
        "calories": result.get("calories", 0) or 0,
        "protein_g": result.get("protein_g", 0) or 0,
        "carbs_g": result.get("carbs_g", 0) or 0,
        "fat_g": result.get("fat_g", 0) or 0,
        "fiber_g": result.get("fiber_g", 0) or 0,
        "sugar_g": result.get("sugar_g", 0) or 0,
        "sodium_mg": result.get("sodium_mg", 0) or 0,
    }
    if micronutrients:
        params["micronutrients"] = json.dumps(micronutrients, ensure_ascii=False, separators=(",", ":"))
    return f"{reverse('nutrition:add')}?{urlencode(params)}"


@login_required
def food_list(request):
    foods = FoodEntry.objects.filter(user=request.user).order_by("-consumed_at", "-id")
    return render(request, "nutrition/food_list.html", {"foods": foods})


@login_required
def food_add(request):
    initial = {}
    source = request.GET.get("source", "manual")
    for key in [
        "name",
        "brand",
        "calories",
        "protein_g",
        "carbs_g",
        "fat_g",
        "fiber_g",
        "sugar_g",
        "sodium_mg",
        "micronutrients",
    ]:
        if key in request.GET:
            value = request.GET.get(key)
            if key == "micronutrients":
                parsed = _normalize_micronutrients(value)
                initial[key] = parsed if parsed else value
            else:
                initial[key] = value
    if request.method == "POST":
        form = FoodEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.source = request.POST.get("source", "manual")
            entry.user = request.user
            entry.save()
            return redirect("nutrition:list")
    else:
        form = FoodEntryForm(initial=initial)
    return render(request, "nutrition/food_form.html", {"form": form, "source": source})


@login_required
def food_edit(request, entry_id: int):
    entry = FoodEntry.objects.filter(user=request.user, id=entry_id).first()
    if not entry:
        messages.error(request, "Food entry not found.")
        return redirect("nutrition:list")
    if request.method == "POST":
        form = FoodEntryForm(request.POST, instance=entry)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.user = request.user
            edited.source = request.POST.get("source", entry.source or "manual")
            edited.save()
            messages.success(request, "Food entry updated.")
            return redirect("nutrition:list")
    else:
        form = FoodEntryForm(instance=entry)
    return render(request, "nutrition/food_form.html", {"form": form, "source": entry.source or "manual"})


@login_required
def food_delete(request, entry_id: int):
    entry = FoodEntry.objects.filter(user=request.user, id=entry_id).first()
    if not entry:
        messages.error(request, "Food entry not found.")
        return redirect("nutrition:list")
    if request.method == "POST":
        entry.delete()
        messages.success(request, "Food entry deleted.")
    return redirect("nutrition:list")


@login_required
def food_lookup(request):
    results = []
    usda_enabled = bool(os.getenv("USDA_API_KEY"))
    form = FoodLookupForm(request.GET or None)
    if form.is_valid():
        results = search_usda_foods(form.cleaned_data["query"])
        for result in results:
            nutrients = result.get("nutrients") or {}
            result["use_url"] = _prefill_add_url(
                source="usda",
                result={
                    "name": result.get("description", ""),
                    "brand": result.get("brand", ""),
                    "calories": nutrients.get("calories", 0),
                    "protein_g": nutrients.get("protein_g", 0),
                    "carbs_g": nutrients.get("carbs_g", 0),
                    "fat_g": nutrients.get("fat_g", 0),
                    "fiber_g": nutrients.get("fiber_g", 0),
                    "sugar_g": nutrients.get("sugar_g", 0),
                    "sodium_mg": nutrients.get("sodium_mg", 0),
                    "micronutrients": nutrients.get("micronutrients", {}),
                },
                default_name=result.get("description", "USDA food"),
            )
        if not results:
            messages.info(request, "No results found right now. Please try again later or add food manually.")
    return render(
        request,
        "nutrition/food_lookup.html",
        {"form": form, "results": results, "usda_enabled": usda_enabled},
    )


@login_required
def food_summary(request):
    period = request.GET.get("period", "day")
    period, start, end, start_dt, end_dt = _period_range(period)
    foods = FoodEntry.objects.filter(user=request.user, consumed_at__range=(start_dt, end_dt))
    calories_in = foods.aggregate(total=Sum("calories"))["total"] or 0
    protein = foods.aggregate(total=Sum("protein_g"))["total"] or 0
    carbs = foods.aggregate(total=Sum("carbs_g"))["total"] or 0
    fat = foods.aggregate(total=Sum("fat_g"))["total"] or 0
    fiber = foods.aggregate(total=Sum("fiber_g"))["total"] or 0
    sugar = foods.aggregate(total=Sum("sugar_g"))["total"] or 0
    sodium = foods.aggregate(total=Sum("sodium_mg"))["total"] or 0
    calories_out = (
        ExerciseEntry.objects.filter(user=request.user, workout__performed_on__range=(start, end)).aggregate(
            total=Sum("calories_burned")
        )["total"]
        or 0
    )
    net = calories_in - calories_out
    net_state = "surplus" if net > 0 else "deficit" if net < 0 else "balance"
    water_total = (
        WaterEntry.objects.filter(user=request.user, consumed_at__range=(start_dt, end_dt)).aggregate(
            total=Sum("amount_ml")
        )["total"]
        or 0
    )

    _micro_labels = {
        "fiber_g": "Fiber (g)",
        "sodium_mg": "Sodium (mg)",
        "iron_mg": "Iron (mg)",
        "calcium_mg": "Calcium (mg)",
        "vitamin_c_mg": "Vitamin C (mg)",
        "potassium_mg": "Potassium (mg)",
        "vitamin_a_mcg": "Vitamin A (mcg)",
        "vitamin_d_mcg": "Vitamin D (mcg)",
        "zinc_mg": "Zinc (mg)",
        "magnesium_mg": "Magnesium (mg)",
    }

    micros_total = {}
    for item in foods:
        data = item.micronutrients or {}
        if isinstance(data, dict):
            for k, v in data.items():
                try:
                    micros_total[k] = float(micros_total.get(k, 0)) + float(v)
                except (TypeError, ValueError):
                    continue
    if "fiber_g" not in micros_total and fiber:
        micros_total["fiber_g"] = float(fiber)
    if "sodium_mg" not in micros_total and sodium:
        micros_total["sodium_mg"] = float(sodium)

    micros_display = []
    for key, value in micros_total.items():
        label = _micro_labels.get(key, key.replace("_", " ").title())
        ref = micro_recommended.get(key)
        micros_display.append({"label": label, "value": value, "reference": ref})

    macro_recommended = {"protein_g": 50, "carbs_g": 275, "fat_g": 78}
    micro_recommended = {"fiber_g": 28, "sodium_mg": 2300, "iron_mg": 18, "calcium_mg": 1300, "vitamin_c_mg": 90}
    macro_pct = {
        "protein_g": round((float(protein) / macro_recommended["protein_g"]) * 100, 1) if protein else 0,
        "carbs_g": round((float(carbs) / macro_recommended["carbs_g"]) * 100, 1) if carbs else 0,
        "fat_g": round((float(fat) / macro_recommended["fat_g"]) * 100, 1) if fat else 0,
    }
    micro_pct = {}
    for key, rec in micro_recommended.items():
        current = micros_total.get(key, 0)
        try:
            micro_pct[key] = round((float(current) / float(rec)) * 100, 1) if current else 0
        except (TypeError, ValueError, ZeroDivisionError):
            micro_pct[key] = 0

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    water_goal_ml = profile.daily_water_goal_ml or 3000

    return render(
        request,
        "nutrition/food_summary.html",
        {
            "period": period,
            "calories_in": calories_in,
            "calories_out": calories_out,
            "net": net,
            "net_state": net_state,
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
            "fiber": fiber,
            "sugar": sugar,
            "sodium": sodium,
            "water_total": water_total,
            "water_goal_ml": water_goal_ml,
            "macro_recommended": macro_recommended,
            "micro_recommended": micro_recommended,
            "macro_pct": macro_pct,
            "micros_total": micros_total,
            "micros_display": micros_display,
            "micro_pct": micro_pct,
        },
    )


@login_required
def water_list(request):
    period = request.GET.get("period", "day")
    period, start, end, start_dt, end_dt = _period_range(period)
    entries = list(
        WaterEntry.objects.filter(user=request.user, consumed_at__range=(start_dt, end_dt)).order_by("-consumed_at", "-id")
    )
    today = timezone.localdate()
    today_total = (
        WaterEntry.objects.filter(user=request.user, consumed_at__date=today).aggregate(total=Sum("amount_ml"))["total"] or 0
    )
    period_total = (
        WaterEntry.objects.filter(user=request.user, consumed_at__range=(start_dt, end_dt)).aggregate(total=Sum("amount_ml"))[
            "total"
        ]
        or 0
    )
    days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    prev_start_dt = timezone.make_aware(datetime.combine(prev_start, time.min))
    prev_end_dt = timezone.make_aware(datetime.combine(prev_end, time.max))
    previous_period_total = (
        WaterEntry.objects.filter(user=request.user, consumed_at__range=(prev_start_dt, prev_end_dt)).aggregate(
            total=Sum("amount_ml")
        )["total"]
        or 0
    )
    period_trend_ml = float(period_total) - float(previous_period_total)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    water_goal_ml = profile.daily_water_goal_ml or 3000
    progress_pct = min(100, round((float(today_total) / float(water_goal_ml)) * 100, 1)) if water_goal_ml else 0
    today_total_oz = round(float(today_total) / 29.5735, 2) if today_total else 0
    period_total_oz = round(float(period_total) / 29.5735, 2) if period_total else 0
    for e in entries:
        e.amount_oz = round(float(e.amount_ml) / 29.5735, 2) if e.amount_ml else 0
    return render(
        request,
        "nutrition/water_list.html",
        {
            "entries": entries,
            "period": period,
            "period_total": period_total,
            "period_total_oz": period_total_oz,
            "period_trend_ml": period_trend_ml,
            "today_total": today_total,
            "today_total_oz": today_total_oz,
            "water_goal_ml": water_goal_ml,
            "progress_pct": progress_pct,
        },
    )


@login_required
def water_add(request):
    if request.method == "POST":
        form = WaterEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            return redirect("nutrition:water_list")
    else:
        form = WaterEntryForm()
    return render(request, "nutrition/water_form.html", {"form": form, "mode": "add"})


@login_required
def water_edit(request, entry_id: int):
    entry = WaterEntry.objects.filter(user=request.user, id=entry_id).first()
    if not entry:
        messages.error(request, "Water entry not found.")
        return redirect("nutrition:water_list")
    if request.method == "POST":
        form = WaterEntryForm(request.POST, instance=entry)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.user = request.user
            updated.save()
            messages.success(request, "Water entry updated.")
            return redirect("nutrition:water_list")
    else:
        form = WaterEntryForm(instance=entry)
    return render(request, "nutrition/water_form.html", {"form": form, "mode": "edit"})


@login_required
def water_delete(request, entry_id: int):
    entry = WaterEntry.objects.filter(user=request.user, id=entry_id).first()
    if not entry:
        messages.error(request, "Water entry not found.")
        return redirect("nutrition:water_list")
    if request.method == "POST":
        entry.delete()
        messages.success(request, "Water entry deleted.")
    return redirect("nutrition:water_list")


@login_required
def food_photo_upload(request):
    if request.method == "POST":
        form = FoodPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.user = request.user
            photo.save()
            try:
                result = recognize_food(photo.image.path)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Food recognition failed (user_id=%s, photo_id=%s)", request.user.id, photo.id)
                photo.status = "failed"
                photo.error_message = "recognition_failed"
                photo.save()
                messages.error(request, "Image recognition failed.")
                return redirect("nutrition:photo_upload")

            photo.status = "processed"
            photo.recognized_name = result.get("name", "")
            photo.recognized_payload = result
            photo.save()
            messages.success(request, "Food recognized. Review and edit values before saving.")
            return redirect(_prefill_add_url(source="image", result=result, default_name="Recognized food"))
    else:
        form = FoodPhotoForm()
    return render(request, "nutrition/food_photo.html", {"form": form})


@login_required
def food_estimate(request):
    if request.method == "POST":
        form = FoodEstimateForm(request.POST)
        if form.is_valid():
            try:
                result = estimate_food_from_text(form.cleaned_data["description"])
            except Exception:  # noqa: BLE001
                logger.exception("Text nutrition estimation failed (user_id=%s)", request.user.id)
                messages.error(request, "Nutrition estimation failed. Please retry or use manual entry.")
                return redirect("nutrition:estimate")
            messages.success(request, "Estimate generated. Review and edit values before saving.")
            return redirect(_prefill_add_url(source="manual", result=result, default_name="Estimated meal"))
    else:
        form = FoodEstimateForm()
    return render(request, "nutrition/food_estimate.html", {"form": form})
