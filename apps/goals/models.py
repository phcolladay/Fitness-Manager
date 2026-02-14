from django.conf import settings
from django.db import models
from django.utils import timezone


class Goal(models.Model):
    GOAL_TYPES = [
        ("calories", "Calories"),
        ("net_calories", "Net Calories"),
        ("protein", "Protein"),
        ("carbs", "Carbs"),
        ("fat", "Fat"),
        ("water", "Water"),
        ("workout_minutes", "Workout Minutes"),
        ("workouts_per_week", "Workouts Per Week"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goals",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    goal_type = models.CharField(max_length=30, choices=GOAL_TYPES)
    target_value = models.DecimalField(max_digits=8, decimal_places=2)
    unit = models.CharField(max_length=30, default="")
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=True)
    notify_push = models.BooleanField(default=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name
