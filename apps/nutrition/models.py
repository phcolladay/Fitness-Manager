from django.conf import settings
from django.db import models
from django.utils import timezone


class FoodEntry(models.Model):
    SOURCE_CHOICES = [
        ("manual", "Manual"),
        ("usda", "USDA API"),
        ("image", "Image Recognition"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="food_entries",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=150)
    brand = models.CharField(max_length=100, blank=True)
    quantity = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    unit = models.CharField(max_length=30, default="serving")
    calories = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    protein_g = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    carbs_g = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    fat_g = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    fiber_g = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    sugar_g = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    sodium_mg = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    micronutrients = models.JSONField(blank=True, null=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="manual")
    consumed_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.name} ({self.calories} kcal)"


class WaterEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="water_entries",
        null=True,
        blank=True,
    )
    amount_ml = models.PositiveIntegerField(default=0)
    consumed_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.amount_ml} ml"


class FoodPhoto(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processed", "Processed"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="food_photos",
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to="food_photos/")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    recognized_name = models.CharField(max_length=150, blank=True)
    recognized_payload = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"Food photo {self.id}"
