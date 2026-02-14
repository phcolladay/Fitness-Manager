from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.goals.models import Goal


class Notification(models.Model):
    CHANNELS = [
        ("inapp", "In App"),
        ("email", "Email"),
        ("push", "Push"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    channel = models.CharField(max_length=10, choices=CHANNELS, default="inapp")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    goal = models.ForeignKey(Goal, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self) -> str:
        return f"{self.channel}: {self.message[:30]}"

# Create your models here.
