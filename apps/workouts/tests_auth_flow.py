from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.goals.models import Goal
from apps.notifications.models import Notification
from apps.nutrition.models import FoodEntry, WaterEntry
from apps.profiles.models import BodyMeasurement, UserProfile
from apps.workouts.models import ExerciseEntry, Workout, WorkoutPlan
from fitness_manager.auth_views import ResilientPasswordResetView
from fitness_manager.forms import SignupForm


class AuthFlowTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _post_request(self, url_name, data):
        request = self.factory.post(reverse(url_name), data)
        request._dont_enforce_csrf_checks = True
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)
        return request

    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "newuser1",
                "email": "newuser1@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("workouts:home"))
        created = get_user_model().objects.filter(username="newuser1", email="newuser1@example.com").first()
        self.assertIsNotNone(created)
        self.assertEqual(int(self.client.session["_auth_user_id"]), created.id)

    def test_signup_with_email_only_generates_username_and_logs_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "email": "EmailOnly@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        created = get_user_model().objects.filter(email="emailonly@example.com").first()
        self.assertIsNotNone(created)
        self.assertEqual(created.username, "emailonly")
        self.assertEqual(int(self.client.session["_auth_user_id"]), created.id)

    def test_signup_rejects_duplicate_email_case_insensitive(self):
        get_user_model().objects.create_user(
            username="existing",
            email="taken@example.com",
            password="StrongPass123!",
        )

        form = SignupForm(
            {
                "email": "Taken@Example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("An account with this email already exists.", form.errors["email"])

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
        self.assertTrue(UserProfile.objects.filter(user=guest_user).exists())
        self.assertGreaterEqual(FoodEntry.objects.filter(user=guest_user).count(), 80)
        self.assertGreaterEqual(WaterEntry.objects.filter(user=guest_user).count(), 60)
        self.assertGreaterEqual(Workout.objects.filter(user=guest_user).count(), 10)
        self.assertGreaterEqual(ExerciseEntry.objects.filter(user=guest_user).count(), 30)
        self.assertGreaterEqual(WorkoutPlan.objects.filter(user=guest_user).count(), 3)
        self.assertGreaterEqual(Goal.objects.filter(user=guest_user).count(), 5)
        self.assertGreaterEqual(Notification.objects.filter(user=guest_user).count(), 8)
        self.assertGreaterEqual(BodyMeasurement.objects.filter(user=guest_user).count(), 25)

        logout_response = self.client.post(reverse("logout"))
        self.assertEqual(logout_response.status_code, 302)
        self.assertEqual(logout_response["Location"], reverse("login"))
        self.assertFalse(get_user_model().objects.filter(id=user_id).exists())

    def test_guest_login_cleans_up_stale_guest_accounts(self):
        stale = get_user_model().objects.create_user(username="guest_old1234", password="pw")
        get_user_model().objects.filter(id=stale.id).update(date_joined=timezone.now() - timedelta(days=2))

        self.client.post(reverse("guest_login"))

        self.assertFalse(get_user_model().objects.filter(id=stale.id).exists())

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
    )
    def test_password_reset_sends_reset_link(self):
        get_user_model().objects.create_user(
            username="resetuser",
            email="reset@example.com",
            password="OldPass123!",
        )

        request = self._post_request("password_reset", {"email": "reset@example.com"})
        response = ResilientPasswordResetView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["reset@example.com"])
        self.assertIn("/reset/", mail.outbox[0].body)
        self.assertIn("Reset your FitMan password", mail.outbox[0].subject)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
    )
    @patch("django.contrib.auth.forms.EmailMultiAlternatives.send", side_effect=RuntimeError("boom"))
    def test_password_reset_email_failure_renders_form_error(self, _send):
        get_user_model().objects.create_user(
            username="resetfail",
            email="resetfail@example.com",
            password="OldPass123!",
        )

        request = self._post_request("password_reset", {"email": "resetfail@example.com"})
        response = ResilientPasswordResetView.as_view()(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"We couldn&#x27;t send the reset email right now.", response.content)
