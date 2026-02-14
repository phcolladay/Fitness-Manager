from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.goals.models import Goal
from apps.nutrition.models import FoodEntry, WaterEntry
from apps.notifications.models import Notification

from .forms import ExerciseEntryForm, WorkoutForm
from .models import ExerciseEntry, Workout
from .utils import classify_exercise, estimate_calories


@login_required
def home(request):
    today = date.today()
    workouts = Workout.objects.filter(user=request.user).order_by("-performed_on", "-id")[:5]
    calories_in = (
        FoodEntry.objects.filter(user=request.user, consumed_at__date=today).aggregate(total=Sum("calories"))[
            "total"
        ]
        or 0
    )
    calories_out = (
        ExerciseEntry.objects.filter(user=request.user, workout__performed_on=today).aggregate(
            total=Sum("calories_burned")
        )["total"]
        or 0
    )
    water_total = (
        WaterEntry.objects.filter(user=request.user, consumed_at__date=today).aggregate(total=Sum("amount_ml"))[
            "total"
        ]
        or 0
    )
    goals = Goal.objects.filter(user=request.user, active=True).order_by("end_date")[:5]
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:5]

    context = {
        "workouts": workouts,
        "calories_in": calories_in,
        "calories_out": calories_out,
        "net_calories": calories_in - calories_out,
        "water_total": water_total,
        "goals": goals,
        "notifications": notifications,
    }
    return render(request, "workouts/home.html", context)


@login_required
def workout_list(request):
    workouts = Workout.objects.filter(user=request.user).order_by("-performed_on", "-id")
    return render(request, "workouts/workout_list.html", {"workouts": workouts})


@login_required
def workout_add(request):
    if request.method == "POST":
        form = WorkoutForm(request.POST)
        if form.is_valid():
            workout = form.save(commit=False)
            workout.user = request.user
            workout.save()
            return redirect("workouts:detail", workout_id=workout.id)
    else:
        form = WorkoutForm()
    return render(request, "workouts/workout_form.html", {"form": form})


@login_required
def workout_detail(request, workout_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    return render(request, "workouts/workout_detail.html", {"workout": workout})


@login_required
def exercise_add(request, workout_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    if request.method == "POST":
        form = ExerciseEntryForm(request.POST)
        if form.is_valid():
            exercise = form.save(commit=False)
            if not exercise.category or not exercise.muscle_group:
                exercise.category, exercise.muscle_group = classify_exercise(
                    exercise.exercise_name
                )
                exercise.auto_classified = True
            if not exercise.calories_burned and exercise.duration_minutes:
                exercise.calories_burned = estimate_calories(
                    exercise.category, exercise.duration_minutes
                )
            exercise.workout = workout
            exercise.user = request.user
            exercise.save()
            return redirect("workouts:detail", workout_id=workout.id)
    else:
        form = ExerciseEntryForm()
    return render(
        request,
        "workouts/exercise_form.html",
        {"form": form, "workout": workout},
    )
