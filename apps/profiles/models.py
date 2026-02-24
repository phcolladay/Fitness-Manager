from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    SEX_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    ACTIVITY_CHOICES = [
        ("sedentary", "Sedentary"),
        ("light", "Lightly active"),
        ("moderate", "Moderately active"),
        ("active", "Active"),
        ("very_active", "Very active"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True)
    age_years = models.PositiveIntegerField(null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default="moderate")
    daily_water_goal_ml = models.PositiveIntegerField(default=3000)
    updated_at = models.DateTimeField(auto_now=True)

    def activity_multiplier(self) -> Decimal:
        mapping = {
            "sedentary": Decimal("1.2"),
            "light": Decimal("1.375"),
            "moderate": Decimal("1.55"),
            "active": Decimal("1.725"),
            "very_active": Decimal("1.9"),
        }
        return mapping.get(self.activity_level, Decimal("1.55"))

    def estimated_daily_calories(self) -> int | None:
        """
        Estimate maintenance calories using Mifflin-St Jeor (when required fields are present).
        """
        if not (self.weight_kg and self.height_cm and self.age_years and self.sex in {"male", "female"}):
            return None
        weight = Decimal(self.weight_kg)
        height = Decimal(self.height_cm)
        age = Decimal(self.age_years)
        bmr = (Decimal("10") * weight) + (Decimal("6.25") * height) - (Decimal("5") * age)
        bmr += Decimal("5") if self.sex == "male" else Decimal("-161")
        return int((bmr * self.activity_multiplier()).quantize(Decimal("1")))

    def __str__(self) -> str:
        return f"Profile<{self.user_id}>"


class BodyMeasurement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="body_measurements")
    measured_on = models.DateField(default=timezone.localdate)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    waist_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    chest_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hip_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    body_fat_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-measured_on", "-id"]

    def __str__(self) -> str:
        return f"{self.measured_on} - {self.weight_kg}kg"

# Create your models here.
