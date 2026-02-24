from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from .services import send_notification


class NotificationServiceTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
        DEFAULT_NOTIFICATION_EMAIL="fallback@example.com",
    )
    def test_email_notification_uses_user_email(self):
        user = get_user_model().objects.create_user(username="u1", password="pw", email="u1@example.com")
        n = send_notification(user=user, message="hello", channel="email")

        self.assertEqual(n.status, "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "noreply@example.com")
        self.assertEqual(mail.outbox[0].to, ["u1@example.com"])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
        DEFAULT_NOTIFICATION_EMAIL="fallback@example.com",
    )
    def test_email_notification_falls_back_to_default_recipient(self):
        user = get_user_model().objects.create_user(username="u2", password="pw", email="")
        n = send_notification(user=user, message="hello", channel="email")

        self.assertEqual(n.status, "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["fallback@example.com"])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_NOTIFICATION_EMAIL="",
    )
    def test_email_notification_fails_without_recipient(self):
        user = get_user_model().objects.create_user(username="u3", password="pw", email="")
        n = send_notification(user=user, message="hello", channel="email")
        self.assertEqual(n.status, "failed")
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_NOTIFICATION_EMAIL="fallback@example.com",
    )
    def test_email_notification_marks_failed_on_send_error(self):
        user = get_user_model().objects.create_user(username="u4", password="pw", email="u4@example.com")
        with patch("apps.notifications.services.send_mail", side_effect=RuntimeError("boom")):
            n = send_notification(user=user, message="hello", channel="email")
        self.assertEqual(n.status, "failed")
