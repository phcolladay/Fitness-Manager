from datetime import date, datetime, time, timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.nutrition.models import FoodEntry, WaterEntry
from apps.workouts.models import ExerciseEntry, Workout


def _date_range(goal_start: date) -> tuple[date, date]:
    end = timezone.localdate()
    start = goal_start or end - timedelta(days=7)
    return start, end


def _datetime_range(start: date, end: date) -> tuple[datetime, datetime]:
    start_dt = timezone.make_aware(datetime.combine(start, time.min))
    end_dt = timezone.make_aware(datetime.combine(end, time.max))
    return start_dt, end_dt


def calculate_goal_progress(goal) -> float:
    if not getattr(goal, "user_id", None):
        return 0.0
    start, end = _date_range(goal.start_date)
    start_dt, end_dt = _datetime_range(start, end)
    if goal.goal_type == "calories":
        total = (
            FoodEntry.objects.filter(user=goal.user, consumed_at__range=(start_dt, end_dt)).aggregate(
                total=Sum("calories")
            )["total"]
            or 0
        )
        return float(total)
    if goal.goal_type == "net_calories":
        calories_in = (
            FoodEntry.objects.filter(user=goal.user, consumed_at__range=(start_dt, end_dt)).aggregate(
                total=Sum("calories")
            )["total"]
            or 0
        )
        calories_out = (
            ExerciseEntry.objects.filter(user=goal.user, workout__performed_on__range=(start, end)).aggregate(
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
            ExerciseEntry.objects.filter(user=goal.user, workout__performed_on__range=(start, end)).aggregate(
                total=Sum("duration_minutes")
            )["total"]
            or 0
        )
        return float(total)
    if goal.goal_type == "workouts_per_week":
        total = (
            Workout.objects.filter(user=goal.user, performed_on__range=(start, end))
            .values("performed_on")
            .distinct()
            .count()
        )
        return float(total)
    return 0.0
