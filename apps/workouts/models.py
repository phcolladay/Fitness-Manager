from django.conf import settings
from django.db import models
from django.utils import timezone


class Workout(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workouts",
    )
    name = models.CharField(max_length=120)
    performed_on = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.performed_on})"


class ExerciseEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exercise_entries",
    )
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name="exercises")
    exercise_name = models.CharField(max_length=120)
    category = models.CharField(max_length=50, blank=True)
    muscle_group = models.CharField(max_length=50, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    calories_burned = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    auto_classified = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.exercise_name} - {self.duration_minutes} min"
