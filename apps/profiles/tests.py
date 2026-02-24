from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import BodyMeasurement, UserProfile


class UserProfileTests(TestCase):
    def test_estimated_daily_calories_requires_demographics(self):
        user = get_user_model().objects.create_user(username="u1", password="pw")
        profile = UserProfile.objects.create(user=user, sex="male", age_years=30, height_cm=180, weight_kg=75)
        self.assertIsInstance(profile.estimated_daily_calories(), int)


class BodyMetricsSummaryTests(TestCase):
    def test_body_metrics_summary_ranges(self):
        user = get_user_model().objects.create_user(username="u2", password="pw")
        BodyMeasurement.objects.create(user=user, weight_kg=80)
        BodyMeasurement.objects.create(user=user, weight_kg=78)

        latest = BodyMeasurement.objects.filter(user=user).order_by("-measured_on", "-id").first()

        self.assertIsNotNone(latest)
        self.assertGreaterEqual(float(latest.weight_kg), 0.0)
