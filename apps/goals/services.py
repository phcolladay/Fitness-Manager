from datetime import date, datetime, time, timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.nutrition.models import FoodEntry, WaterEntry
from apps.workouts.models import ExerciseEntry, Workout
from apps.workouts.models import ExerciseLibrary


def _today_range() -> tuple[datetime, datetime]:
    """Return datetime range covering today only."""
    today = timezone.localdate()
    start_dt = timezone.make_aware(datetime.combine(today, time.min))
    end_dt = timezone.make_aware(datetime.combine(today, time.max))
    return start_dt, end_dt


def _week_range() -> tuple[date, date]:
    """Return date range covering the current ISO week (Mon–Sun)."""
    today = timezone.localdate()
    start = today - timedelta(days=today.weekday())  # Monday
    return start, today


def calculate_goal_progress(goal) -> float:
    if not getattr(goal, "user_id", None):
        return 0.0

    # Daily goals: only count today's data
    daily_types = {"calories", "net_calories", "protein", "carbs", "fat", "water"}
    # Weekly goals: count current week's data
    weekly_types = {"workout_minutes", "workouts_per_week"}

    if goal.goal_type in daily_types:
        start_dt, end_dt = _today_range()
    elif goal.goal_type in weekly_types:
        week_start, week_end = _week_range()
    else:
        return 0.0

    if goal.goal_type == "calories":
        total = (
            FoodEntry.objects.filter(user=goal.user, consumed_at__range=(start_dt, end_dt)).aggregate(
                total=Sum("calories")
            )["total"]
            or 0
        )
        return float(total)
    if goal.goal_type == "net_calories":
        today = timezone.localdate()
        calories_in = (
            FoodEntry.objects.filter(user=goal.user, consumed_at__range=(start_dt, end_dt)).aggregate(
                total=Sum("calories")
            )["total"]
            or 0
        )
        calories_out = (
            ExerciseEntry.objects.filter(user=goal.user, workout__performed_on=today).aggregate(
                total=Sum("calories_burned")
            )["total"]
            or 0
        )
        return float(calories_in - calories_out)
    if goal.goal_type == "protein":
        total = (
            FoodEntry.objects.filter(user=goal.user, consumed_at__range=(start_dt, end_dt)).aggregate(
                total=Sum("protein_g")
            )["total"]
            or 0
        )
        return float(total)
    if goal.goal_type == "carbs":
        total = (
            FoodEntry.objects.filter(user=goal.user, consumed_at__range=(start_dt, end_dt)).aggregate(
                total=Sum("carbs_g")
            )["total"]
            or 0
        )
        return float(total)
    if goal.goal_type == "fat":
        total = (
            FoodEntry.objects.filter(user=goal.user, consumed_at__range=(start_dt, end_dt)).aggregate(
                total=Sum("fat_g")
            )["total"]
            or 0
        )
        return float(total)
    if goal.goal_type == "water":
        total = (
            WaterEntry.objects.filter(user=goal.user, consumed_at__range=(start_dt, end_dt)).aggregate(
                total=Sum("amount_ml")
            )["total"]
            or 0
        )
        return float(total)
    if goal.goal_type == "workout_minutes":
        total = (
            ExerciseEntry.objects.filter(user=goal.user, workout__performed_on__range=(week_start, week_end)).aggregate(
                total=Sum("duration_minutes")
            )["total"]
            or 0
        )
        return float(total)
    if goal.goal_type == "workouts_per_week":
        total = (
            Workout.objects.filter(user=goal.user, performed_on__range=(week_start, week_end))
            .values("performed_on")
            .distinct()
            .count()
        )
        return float(total)
    return 0.0


def recommend_exercises_for_goal(goal_type: str, limit: int = 5):
    category_map = {
        "workout_minutes": ["cardio", "strength"],
        "workouts_per_week": ["strength", "cardio"],
        "calories": ["cardio"],
        "net_calories": ["cardio", "hiit"],
    }
    categories = category_map.get(goal_type, [])
    qs = ExerciseLibrary.objects.all()
    if categories:
        qs = qs.filter(category__in=categories)
    results = list(qs[:limit])
    if len(results) < limit:
        existing_names = {r.name for r in results}
        extra = ExerciseLibrary.objects.exclude(name__in=existing_names)[: max(0, limit - len(results))]
        results.extend(list(extra))
    return results
