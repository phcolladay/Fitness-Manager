from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.goals.models import Goal
from apps.nutrition.models import FoodEntry, WaterEntry
from apps.notifications.models import Notification
from apps.profiles.models import UserProfile

from .forms import ExerciseEntryForm, WorkoutForm, WorkoutPlanForm
from .models import ExerciseEntry, ExerciseLibrary, Workout, WorkoutPlan
from .utils import classify_exercise, estimate_calories


def _workout_period(period: str):
    today = timezone.localdate()
    if period == "month":
        days = 30
    elif period == "day":
        days = 1
    else:
        period = "week"
        days = 7
    start = today - timedelta(days=days - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return period, start, today, prev_start, prev_end


@login_required
def home(request):
    today = date.today()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
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
    recommended_calories = profile.estimated_daily_calories()
    water_goal_ml = profile.daily_water_goal_ml or 3000
    water_progress_pct = min(100, round((float(water_total) / float(water_goal_ml)) * 100, 1)) if water_goal_ml else 0

    context = {
        "workouts": workouts,
        "calories_in": calories_in,
        "calories_out": calories_out,
        "net_calories": calories_in - calories_out,
        "recommended_calories": recommended_calories,
        "water_total": water_total,
        "water_goal_ml": water_goal_ml,
        "water_progress_pct": water_progress_pct,
        "goals": goals,
        "notifications": notifications,
    }
    return render(request, "workouts/home.html", context)


@login_required
def workout_list(request):
    period = request.GET.get("period", "week")
    period, start, end, prev_start, prev_end = _workout_period(period)
    workouts = Workout.objects.filter(user=request.user, performed_on__range=(start, end)).order_by("-performed_on", "-id")
    period_minutes = (
        ExerciseEntry.objects.filter(user=request.user, workout__performed_on__range=(start, end)).aggregate(
            total=Sum("duration_minutes")
        )["total"]
        or 0
    )
    previous_minutes = (
        ExerciseEntry.objects.filter(
            user=request.user, workout__performed_on__range=(prev_start, prev_end)
        ).aggregate(total=Sum("duration_minutes"))["total"]
        or 0
    )
    period_calories = (
        ExerciseEntry.objects.filter(user=request.user, workout__performed_on__range=(start, end)).aggregate(
            total=Sum("calories_burned")
        )["total"]
        or 0
    )
    trend_delta = float(period_minutes) - float(previous_minutes)
    return render(
        request,
        "workouts/workout_list.html",
        {
            "workouts": workouts,
            "period": period,
            "period_minutes": period_minutes,
            "previous_minutes": previous_minutes,
            "period_calories": period_calories,
            "trend_delta": trend_delta,
        },
    )


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
def workout_edit(request, workout_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    if request.method == "POST":
        form = WorkoutForm(request.POST, instance=workout)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.user = request.user
            edited.save()
            messages.success(request, "Workout updated.")
            return redirect("workouts:detail", workout_id=workout.id)
    else:
        form = WorkoutForm(instance=workout)
    return render(request, "workouts/workout_form.html", {"form": form, "mode": "edit"})


@login_required
def workout_delete(request, workout_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    if request.method == "POST":
        workout.delete()
        messages.success(request, "Workout deleted.")
    return redirect("workouts:list")


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


@login_required
def exercise_edit(request, workout_id: int, exercise_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    exercise = get_object_or_404(ExerciseEntry, id=exercise_id, workout=workout, user=request.user)
    if request.method == "POST":
        form = ExerciseEntryForm(request.POST, instance=exercise)
        if form.is_valid():
            updated = form.save(commit=False)
            if not updated.category or not updated.muscle_group:
                updated.category, updated.muscle_group = classify_exercise(updated.exercise_name)
                updated.auto_classified = True
            if not updated.calories_burned and updated.duration_minutes:
                updated.calories_burned = estimate_calories(updated.category, updated.duration_minutes)
            updated.user = request.user
            updated.workout = workout
            updated.save()
            messages.success(request, "Exercise updated.")
            return redirect("workouts:detail", workout_id=workout.id)
    else:
        form = ExerciseEntryForm(instance=exercise)
    return render(request, "workouts/exercise_form.html", {"form": form, "workout": workout, "mode": "edit"})


@login_required
def exercise_delete(request, workout_id: int, exercise_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    exercise = get_object_or_404(ExerciseEntry, id=exercise_id, workout=workout, user=request.user)
    if request.method == "POST":
        exercise.delete()
        messages.success(request, "Exercise deleted.")
    return redirect("workouts:detail", workout_id=workout.id)


@login_required
def exercise_library(request):
    q = (request.GET.get("q") or "").strip()
    items = ExerciseLibrary.objects.all()
    if q:
        items = items.filter(
            Q(name__icontains=q)
            | Q(category__icontains=q)
            | Q(muscle_group__icontains=q)
            | Q(description__icontains=q)
            | Q(instructions__icontains=q)
        )
    return render(request, "workouts/exercise_library.html", {"items": items, "q": q})


@login_required
def plan_list(request):
    plans = WorkoutPlan.objects.filter(user=request.user).order_by("-updated_at", "-id")
    return render(request, "workouts/plan_list.html", {"plans": plans})


@login_required
def plan_add(request):
    if request.method == "POST":
        form = WorkoutPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user = request.user
            plan.save()
            messages.success(request, "Workout plan created.")
            return redirect("workouts:plan_list")
    else:
        form = WorkoutPlanForm()
    return render(request, "workouts/plan_form.html", {"form": form, "mode": "add"})


@login_required
def plan_edit(request, plan_id: int):
    plan = get_object_or_404(WorkoutPlan, id=plan_id, user=request.user)
    if request.method == "POST":
        form = WorkoutPlanForm(request.POST, instance=plan)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.user = request.user
            updated.save()
            messages.success(request, "Workout plan updated.")
            return redirect("workouts:plan_list")
    else:
        form = WorkoutPlanForm(instance=plan)
    return render(request, "workouts/plan_form.html", {"form": form, "mode": "edit"})


@login_required
def plan_delete(request, plan_id: int):
    plan = get_object_or_404(WorkoutPlan, id=plan_id, user=request.user)
    if request.method == "POST":
        plan.delete()
        messages.success(request, "Workout plan deleted.")
    return redirect("workouts:plan_list")
