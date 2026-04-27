from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.notifications.models import Notification

User = get_user_model()


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="notifmodeluser", password="pass")

    def test_str(self):
        notif = Notification.objects.create(
            user=self.user,
            channel="inapp",
            status="pending",
            message="You reached your protein goal!",
        )
        result = str(notif)
        # __str__ should include something meaningful — channel, status, or message snippet
        self.assertTrue(len(result) > 0)

    def test_str_contains_channel_or_status(self):
        notif = Notification.objects.create(
            user=self.user,
            channel="email",
            status="sent",
            message="Weekly summary",
        )
        result = str(notif)
        self.assertTrue(
            "email" in result.lower() or "sent" in result.lower() or "weekly" in result.lower(),
            f"__str__ output '{result}' does not contain expected content",
        )


class NotificationListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="notiflistuser", password="pass")
        self.other_user = User.objects.create_user(username="notifotheruser", password="pass")
        self.client.login(username="notiflistuser", password="pass")

    def _make_notification(self, user, message="Test notification", channel="inapp", status="pending"):
        return Notification.objects.create(
            user=user,
            channel=channel,
            status=status,
            message=message,
        )

    def test_get_returns_200(self):
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("notifications:list"))
        self.assertNotEqual(response.status_code, 200)

    def test_shows_only_current_users_notifications(self):
        own_notif = self._make_notification(self.user, message="Mine")
        other_notif = self._make_notification(self.other_user, message="Not mine")

        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)
        context_notifs = list(response.context["notifications"])
        ids_in_context = [n.id for n in context_notifs]
        self.assertIn(own_notif.id, ids_in_context)
        self.assertNotIn(other_notif.id, ids_in_context)

    def test_ordered_by_created_at_descending(self):
        notif_a = self._make_notification(self.user, message="First notification")
        notif_b = self._make_notification(self.user, message="Second notification")
        notif_c = self._make_notification(self.user, message="Third notification")

        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)
        context_notifs = list(response.context["notifications"])
        ids_in_context = [n.id for n in context_notifs]
        idx_c = ids_in_context.index(notif_c.id)
        idx_b = ids_in_context.index(notif_b.id)
        idx_a = ids_in_context.index(notif_a.id)
        self.assertLess(idx_c, idx_b)
        self.assertLess(idx_b, idx_a)

    def test_empty_list_returns_200(self):
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)

    def test_all_channels_appear_in_list(self):
        for channel, _ in Notification.CHANNELS:
            self._make_notification(self.user, message=f"{channel} notification", channel=channel)

        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)

    def test_all_statuses_appear_in_list(self):
        for status, _ in Notification.STATUS_CHOICES:
            self._make_notification(self.user, message=f"{status} notification", status=status)

        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)
