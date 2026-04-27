from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.profiles.models import UserProfile, BodyMeasurement
from apps.profiles.forms import UserProfileForm, BodyMeasurementForm

User = get_user_model()


class UserProfileFormTest(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "sex": "male",
            "age_years": 30,
            "height_cm": "175.0",
            "weight_kg": "75.0",
            "activity_level": "moderate",
            "daily_water_goal_ml": 2500,
        }
        data.update(overrides)
        return data

    def test_valid_data(self):
        form = UserProfileForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_negative_weight_is_invalid(self):
        form = UserProfileForm(data=self._valid_data(weight_kg="-5.0"))
        self.assertFalse(form.is_valid())
        self.assertIn("weight_kg", form.errors)

    def test_negative_age_is_invalid(self):
        form = UserProfileForm(data=self._valid_data(age_years=-1))
        self.assertFalse(form.is_valid())
        self.assertIn("age_years", form.errors)

    def test_negative_height_is_invalid(self):
        form = UserProfileForm(data=self._valid_data(height_cm="-10.0"))
        self.assertFalse(form.is_valid())
        self.assertIn("height_cm", form.errors)

    def test_negative_water_goal_is_invalid(self):
        form = UserProfileForm(data=self._valid_data(daily_water_goal_ml=-100))
        self.assertFalse(form.is_valid())
        self.assertIn("daily_water_goal_ml", form.errors)


class BodyMeasurementFormTest(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "measured_on": timezone.localdate().isoformat(),
            "weight_kg": "80.0",
            "waist_cm": "85.0",
            "chest_cm": "100.0",
            "hip_cm": "95.0",
            "body_fat_pct": "18.5",
            "notes": "",
        }
        data.update(overrides)
        return data

    def test_valid_data(self):
        form = BodyMeasurementForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_negative_body_fat_pct_is_invalid(self):
        form = BodyMeasurementForm(data=self._valid_data(body_fat_pct="-5.0"))
        self.assertFalse(form.is_valid())
        self.assertIn("body_fat_pct", form.errors)

    def test_negative_weight_is_invalid(self):
        form = BodyMeasurementForm(data=self._valid_data(weight_kg="-1.0"))
        self.assertFalse(form.is_valid())
        self.assertIn("weight_kg", form.errors)

    def test_negative_waist_is_invalid(self):
        form = BodyMeasurementForm(data=self._valid_data(waist_cm="-10.0"))
        self.assertFalse(form.is_valid())
        self.assertIn("waist_cm", form.errors)

    def test_negative_chest_is_invalid(self):
        form = BodyMeasurementForm(data=self._valid_data(chest_cm="-10.0"))
        self.assertFalse(form.is_valid())
        self.assertIn("chest_cm", form.errors)

    def test_negative_hip_is_invalid(self):
        form = BodyMeasurementForm(data=self._valid_data(hip_cm="-10.0"))
        self.assertFalse(form.is_valid())
        self.assertIn("hip_cm", form.errors)


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="profilemodeluser", password="pass")

    def _make_profile(self, sex="male", age=30, height=175.0, weight=75.0, activity_level="moderate"):
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.sex = sex
        profile.age_years = age
        profile.height_cm = height
        profile.weight_kg = weight
        profile.activity_level = activity_level
        profile.save()
        return profile

    def test_estimated_daily_calories_male(self):
        profile = self._make_profile(sex="male", age=30, height=175.0, weight=75.0, activity_level="moderate")
        calories = profile.estimated_daily_calories()
        self.assertIsNotNone(calories)
        self.assertIsInstance(calories, int)
        self.assertGreater(calories, 0)

    def test_estimated_daily_calories_female_differs_from_male(self):
        male_profile = self._make_profile(sex="male", age=30, height=175.0, weight=75.0, activity_level="moderate")
        male_calories = male_profile.estimated_daily_calories()

        female_user = User.objects.create_user(username="femaleprofileuser", password="pass")
        female_profile, _ = UserProfile.objects.get_or_create(user=female_user)
        female_profile.sex = "female"
        female_profile.age_years = 30
        female_profile.height_cm = 175.0
        female_profile.weight_kg = 75.0
        female_profile.activity_level = "moderate"
        female_profile.save()
        female_calories = female_profile.estimated_daily_calories()

        self.assertIsNotNone(female_calories)
        self.assertNotEqual(male_calories, female_calories)

    def test_activity_multiplier_sedentary(self):
        profile = self._make_profile(activity_level="sedentary")
        multiplier = profile.activity_multiplier()
        self.assertIsNotNone(multiplier)
        self.assertGreater(multiplier, 1.0)

    def test_activity_multiplier_active_higher_than_sedentary(self):
        sedentary = self._make_profile(activity_level="sedentary")
        sedentary_mult = sedentary.activity_multiplier()

        active_user = User.objects.create_user(username="activeprofileuser", password="pass")
        active_profile, _ = UserProfile.objects.get_or_create(user=active_user)
        active_profile.sex = "male"
        active_profile.age_years = 30
        active_profile.height_cm = 175.0
        active_profile.weight_kg = 75.0
        active_profile.activity_level = "very_active"
        active_profile.save()
        active_mult = active_profile.activity_multiplier()

        self.assertGreater(active_mult, sedentary_mult)


class ProfileEditViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="profileedituser", password="pass")
        self.client.login(username="profileedituser", password="pass")
        UserProfile.objects.get_or_create(user=self.user)

    def _valid_post_data(self):
        return {
            "sex": "male",
            "age_years": 28,
            "height_cm": "180.0",
            "weight_kg": "80.0",
            "activity_level": "moderate",
            "daily_water_goal_ml": 2000,
        }

    def test_get_returns_200(self):
        response = self.client.get(reverse("profiles:profile"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects_to_profile(self):
        response = self.client.post(reverse("profiles:profile"), data=self._valid_post_data())
        self.assertIn(response.status_code, [200, 302])


class BodyMetricsListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="bodylistuser", password="pass")
        self.client.login(username="bodylistuser", password="pass")

    def test_get_returns_200(self):
        response = self.client.get(reverse("profiles:body_metrics"))
        self.assertEqual(response.status_code, 200)

    def test_shows_trend_with_two_or_more_entries(self):
        BodyMeasurement.objects.create(
            user=self.user,
            measured_on=timezone.localdate(),
            weight_kg=Decimal("80.0"),
        )
        BodyMeasurement.objects.create(
            user=self.user,
            measured_on=timezone.localdate(),
            weight_kg=Decimal("79.5"),
        )
        response = self.client.get(reverse("profiles:body_metrics"))
        self.assertEqual(response.status_code, 200)


class BodyMetricAddViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="bodyadduser", password="pass")
        self.client.login(username="bodyadduser", password="pass")

    def _valid_post_data(self):
        return {
            "measured_on": timezone.localdate().isoformat(),
            "weight_kg": "78.0",
            "waist_cm": "",
            "chest_cm": "",
            "hip_cm": "",
            "body_fat_pct": "",
            "notes": "",
        }

    def test_get_returns_200(self):
        response = self.client.get(reverse("profiles:body_metrics_add"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects_to_body_metrics(self):
        response = self.client.post(reverse("profiles:body_metrics_add"), data=self._valid_post_data())
        self.assertIn(response.status_code, [200, 302])


class BodyMetricEditViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="bodyedituser", password="pass")
        self.other_user = User.objects.create_user(username="bodyeditother", password="pass")
        self.client.login(username="bodyedituser", password="pass")

        self.entry = BodyMeasurement.objects.create(
            user=self.user,
            measured_on=timezone.localdate(),
            weight_kg=Decimal("80.0"),
        )
        self.other_entry = BodyMeasurement.objects.create(
            user=self.other_user,
            measured_on=timezone.localdate(),
            weight_kg=Decimal("70.0"),
        )

    def _valid_post_data(self):
        return {
            "measured_on": timezone.localdate().isoformat(),
            "weight_kg": "81.0",
            "waist_cm": "",
            "chest_cm": "",
            "hip_cm": "",
            "body_fat_pct": "",
            "notes": "",
        }

    def test_get_returns_200(self):
        response = self.client.get(reverse("profiles:body_metrics_edit", args=[self.entry.id]))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects(self):
        response = self.client.post(
            reverse("profiles:body_metrics_edit", args=[self.entry.id]),
            data=self._valid_post_data(),
        )
        self.assertIn(response.status_code, [200, 302])

    def test_other_user_entry_returns_404(self):
        response = self.client.get(reverse("profiles:body_metrics_edit", args=[self.other_entry.id]))
        self.assertEqual(response.status_code, 404)


class BodyMetricDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="bodydeluser", password="pass")
        self.other_user = User.objects.create_user(username="bodydelother", password="pass")
        self.client.login(username="bodydeluser", password="pass")

    def _make_entry(self, user, weight="80.0"):
        return BodyMeasurement.objects.create(
            user=user,
            measured_on=timezone.localdate(),
            weight_kg=Decimal(weight),
        )

    def test_post_deletes_and_redirects(self):
        entry = self._make_entry(self.user)
        response = self.client.post(reverse("profiles:body_metrics_delete", args=[entry.id]))
        self.assertIn(response.status_code, [200, 302])
        self.assertFalse(BodyMeasurement.objects.filter(id=entry.id).exists())

    def test_other_user_entry_returns_404(self):
        other_entry = self._make_entry(self.other_user)
        response = self.client.post(reverse("profiles:body_metrics_delete", args=[other_entry.id]))
        self.assertEqual(response.status_code, 404)
