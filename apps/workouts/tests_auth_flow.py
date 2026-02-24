from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


class AuthFlowTests(TestCase):
    def test_login_with_email(self):
        user = get_user_model().objects.create_user(
            username="owen",
            email="owen@example.com",
            password="StrongPass123!",
        )
        response = self.client.post(
            reverse("login"),
            {"username": "owen@example.com", "password": "StrongPass123!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("workouts:home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_guest_login_then_logout_deletes_guest_user(self):
        response = self.client.post(reverse("guest_login"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("workouts:home"))

        user_id = int(self.client.session["_auth_user_id"])
        guest_user = get_user_model().objects.get(id=user_id)
        self.assertTrue(guest_user.username.startswith("guest_"))

        logout_response = self.client.post(reverse("logout"))
        self.assertEqual(logout_response.status_code, 302)
        self.assertEqual(logout_response["Location"], reverse("login"))
        self.assertFalse(get_user_model().objects.filter(id=user_id).exists())

    def test_guest_login_cleans_up_stale_guest_accounts(self):
        stale = get_user_model().objects.create_user(username="guest_old1234", password="pw")
        get_user_model().objects.filter(id=stale.id).update(date_joined=timezone.now() - timedelta(days=2))

        self.client.post(reverse("guest_login"))

        self.assertFalse(get_user_model().objects.filter(id=stale.id).exists())
