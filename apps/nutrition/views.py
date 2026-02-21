import logging
import os

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import FoodEntryForm, FoodLookupForm, FoodPhotoForm, WaterEntryForm
from .models import FoodEntry, FoodPhoto, WaterEntry
from .services import search_usda_foods
from .vision import recognize_food

logger = logging.getLogger(__name__)


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
    ]:
        if key in request.GET:
            initial[key] = request.GET.get(key)
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
def food_lookup(request):
    results = []
    usda_enabled = bool(os.getenv("USDA_API_KEY"))
    form = FoodLookupForm(request.GET or None)
    if form.is_valid():
        results = search_usda_foods(form.cleaned_data["query"])
        if not results:
            messages.info(request, "No USDA results found or API key missing.")
    return render(
        request,
        "nutrition/food_lookup.html",
        {"form": form, "results": results, "usda_enabled": usda_enabled},
    )


@login_required
def water_list(request):
    entries = WaterEntry.objects.filter(user=request.user).order_by("-consumed_at", "-id")
    return render(request, "nutrition/water_list.html", {"entries": entries})


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
    return render(request, "nutrition/water_form.html", {"form": form})


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

            FoodEntry.objects.create(
                user=request.user,
                name=photo.recognized_name or "Recognized food",
                calories=result.get("calories", 0) or 0,
                protein_g=result.get("protein_g", 0) or 0,
                carbs_g=result.get("carbs_g", 0) or 0,
                fat_g=result.get("fat_g", 0) or 0,
                fiber_g=result.get("fiber_g", 0) or 0,
                sugar_g=result.get("sugar_g", 0) or 0,
                sodium_mg=result.get("sodium_mg", 0) or 0,
                source="image",
            )
            messages.success(request, "Food recognized and saved.")
            return redirect("nutrition:list")
    else:
        form = FoodPhotoForm()
    return render(request, "nutrition/food_photo.html", {"form": form})
