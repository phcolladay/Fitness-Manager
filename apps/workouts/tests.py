from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.http import Http404
from django.db.models import Q
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from .models import ExerciseEntry, ExerciseLibrary, Workout
from .views import workout_detail


class WorkoutModelTests(TestCase):
    def test_workout_and_exercise_str(self):
        user = get_user_model().objects.create_user(username="u1", password="pw")
        workout = Workout.objects.create(name="Morning Cardio", user=user)
        exercise = ExerciseEntry.objects.create(
            workout=workout,
            user=user,
            exercise_name="Jogging",
            duration_minutes=30,
            calories_burned=250.0,
        )

        self.assertIn("Morning Cardio", str(workout))
        self.assertIn("Jogging", str(exercise))


class WorkoutAuthTests(TestCase):
    def test_home_requires_login(self):
        resp = self.client.get(reverse("workouts:home"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])

    def test_workout_detail_is_scoped_to_user(self):
        User = get_user_model()
        u1 = User.objects.create_user(username="u1", password="pw")
        u2 = User.objects.create_user(username="u2", password="pw")
        workout = Workout.objects.create(name="Secret", user=u1)

        request = RequestFactory().get(reverse("workouts:detail", kwargs={"workout_id": workout.id}))
        request.user = u2
        with self.assertRaises(Http404):
            workout_detail(request, workout_id=workout.id)


class ExerciseLibraryTests(TestCase):
    def test_search_matches_instructions(self):
        ExerciseLibrary.objects.create(
            name="Farmer Carry",
            category="strength",
            muscle_group="full body",
            description="Carry heavy weights for distance.",
            instructions="Walk slowly with tight core and neutral spine.",
        )

        q = "neutral spine"
        results = ExerciseLibrary.objects.filter(
            Q(name__icontains=q)
            | Q(category__icontains=q)
            | Q(muscle_group__icontains=q)
            | Q(description__icontains=q)
            | Q(instructions__icontains=q)
        )
        self.assertTrue(results.filter(name="Farmer Carry").exists())


class ExerciseAIEstimateFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="aiuser", password="pw")
        self.client.login(username="aiuser", password="pw")
        self.workout = Workout.objects.create(name="AI Session", user=self.user)

    @patch("apps.workouts.views.estimate_exercise_calories_ai", return_value=321.5)
    def test_ai_estimate_button_prefills_calories_without_saving(self, _ai):
        url = reverse("workouts:exercise_add", kwargs={"workout_id": self.workout.id})
        response = self.client.post(
            url,
            {
                "exercise_name": "Jump Rope",
                "category": "hiit",
                "muscle_group": "full body",
                "duration_minutes": 30,
                "calories_burned": "",
                "ai_estimate": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ExerciseEntry.objects.count(), 0)
        query = parse_qs(urlparse(response["Location"]).query)
        self.assertEqual(query.get("calories_burned"), ["321.5"])

    @patch("apps.workouts.views.estimate_exercise_calories_ai")
    def test_ai_estimate_button_requires_positive_duration(self, ai):
        url = reverse("workouts:exercise_add", kwargs={"workout_id": self.workout.id})
        response = self.client.post(
            url,
            {
                "exercise_name": "Jump Squats",
                "category": "strength",
                "muscle_group": "legs",
                "duration_minutes": 0,
                "calories_burned": "",
                "ai_estimate": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter duration minutes greater than 0 before estimating calories.")
        self.assertEqual(ExerciseEntry.objects.count(), 0)
        ai.assert_not_called()

    @patch("apps.workouts.views.estimate_exercise_calories_ai", return_value=None)
    def test_ai_estimate_button_prefills_fallback_when_ai_unavailable(self, _ai):
        url = reverse("workouts:exercise_add", kwargs={"workout_id": self.workout.id})
        response = self.client.post(
            url,
            {
                "exercise_name": "Jump Squats",
                "category": "strength",
                "muscle_group": "legs",
                "duration_minutes": 20,
                "calories_burned": "",
                "ai_estimate": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ExerciseEntry.objects.count(), 0)
        query = parse_qs(urlparse(response["Location"]).query)
        self.assertEqual(query.get("calories_burned"), ["120.0"])

    @patch("apps.workouts.views.estimate_exercise_calories_ai", return_value=222.0)
    def test_ai_estimate_button_replaces_existing_calories(self, _ai):
        url = reverse("workouts:exercise_add", kwargs={"workout_id": self.workout.id})
        response = self.client.post(
            url,
            {
                "exercise_name": "Jump Rope",
                "category": "cardio",
                "muscle_group": "full body",
                "duration_minutes": 15,
                "calories_burned": "50",
                "ai_estimate": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ExerciseEntry.objects.count(), 0)
        query = parse_qs(urlparse(response["Location"]).query)
        self.assertEqual(query.get("calories_burned"), ["222.0"])

    @patch("apps.workouts.views.estimate_exercise_calories_ai", return_value=180.25)
    def test_save_uses_ai_when_calories_missing(self, _ai):
        url = reverse("workouts:exercise_add", kwargs={"workout_id": self.workout.id})
        response = self.client.post(
            url,
            {
                "exercise_name": "Jogging",
                "category": "cardio",
                "muscle_group": "legs",
                "duration_minutes": 25,
                "calories_burned": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        entry = ExerciseEntry.objects.get(workout=self.workout)
        self.assertEqual(float(entry.calories_burned), 180.25)

    @patch("apps.workouts.views.estimate_exercise_calories_ai", return_value=None)
    def test_save_falls_back_when_ai_unavailable(self, _ai):
        url = reverse("workouts:exercise_add", kwargs={"workout_id": self.workout.id})
        self.client.post(
            url,
            {
                "exercise_name": "Jogging",
                "category": "cardio",
                "muscle_group": "legs",
                "duration_minutes": 10,
                "calories_burned": "",
            },
        )
        entry = ExerciseEntry.objects.get(workout=self.workout)
        self.assertEqual(float(entry.calories_burned), 80.0)
