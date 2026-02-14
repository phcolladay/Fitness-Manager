from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.http import Http404

from .models import ExerciseEntry, Workout
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
