import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Notification

logger = logging.getLogger(__name__)

def send_notification(*, user, message: str, channel: str = "inapp", goal=None) -> Notification:
    notification = Notification.objects.create(
        user=user,
        channel=channel,
        status="pending",
        message=message,
        goal=goal,
    )
    if channel == "email":
        recipient = getattr(user, "email", "") or settings.DEFAULT_NOTIFICATION_EMAIL
        if not recipient:
            notification.status = "failed"
            notification.sent_at = timezone.now()
            notification.save()
            return notification
        try:
            send_mail(
                "Fitness Manager Goal Update",
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=False,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Email notification failed (user_id=%s)", getattr(user, "id", None))
            notification.status = "failed"
            notification.sent_at = timezone.now()
            notification.save(update_fields=["status", "sent_at"])
            return notification
        else:
            notification.status = "sent"
            notification.sent_at = timezone.now()
            notification.save(update_fields=["status", "sent_at"])
            return notification

    if channel == "push":
        notification.status = "sent"
        notification.sent_at = timezone.now()
        notification.save(update_fields=["status", "sent_at"])
        return notification

    notification.status = "sent"
    notification.sent_at = timezone.now()
    notification.save(update_fields=["status", "sent_at"])
    return notification
