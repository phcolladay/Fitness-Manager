from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.goals.models import Goal
from apps.goals.services import calculate_goal_progress
from apps.notifications.services import send_notification


class Command(BaseCommand):
    help = "Send goal reminder notifications via email/push/in-app."

    def handle(self, *args, **options):
        now = timezone.now()
        for goal in Goal.objects.filter(active=True).select_related("user"):
            if not goal.user_id:
                continue
            if goal.last_notified_at and goal.last_notified_at > now - timedelta(days=1):
                continue
            progress = calculate_goal_progress(goal)
            if progress >= float(goal.target_value):
                continue
            message = (
                f"Goal reminder: {goal.name} is at {progress} {goal.unit}. "
                f"Target is {goal.target_value} {goal.unit}."
            )
            if goal.notify_email:
                send_notification(user=goal.user, message=message, channel="email", goal=goal)
            if goal.notify_push:
                send_notification(user=goal.user, message=message, channel="push", goal=goal)
            send_notification(user=goal.user, message=message, channel="inapp", goal=goal)
            goal.last_notified_at = now
            goal.save(update_fields=["last_notified_at"])
