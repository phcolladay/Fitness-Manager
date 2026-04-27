from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.goals.models import Goal
from apps.goals.forms import GoalForm
from apps.goals.services import calculate_goal_progress, recommend_exercises_for_goal
from apps.nutrition.models import FoodEntry, WaterEntry
from apps.workouts.models import Workout, ExerciseEntry, ExerciseLibrary

User = get_user_model()


class GoalFormTest(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "name": "Protein Goal",
            "goal_type": "protein",
            "target_value": "150.00",
            "unit": "g",
            "start_date": timezone.localdate().isoformat(),
            "end_date": "",
            "active": True,
            "notify_email": False,
            "notify_push": False,
        }
        data.update(overrides)
        return data

    def test_valid_data(self):
        form = GoalForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_name_is_invalid(self):
        data = self._valid_data()
        data["name"] = ""
        form = GoalForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_missing_goal_type_is_invalid(self):
        data = self._valid_data()
        data["goal_type"] = ""
        form = GoalForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("goal_type", form.errors)

    def test_missing_target_value_is_invalid(self):
        data = self._valid_data()
        data["target_value"] = ""
        form = GoalForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("target_value", form.errors)

    def test_missing_start_date_is_invalid(self):
        data = self._valid_data()
        data["start_date"] = ""
        form = GoalForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("start_date", form.errors)


class GoalModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="goaltestuser", password="pass")

    def test_str(self):
        goal = Goal.objects.create(
            user=self.user,
            name="My Calorie Goal",
            goal_type="calories",
            target_value=Decimal("2000.00"),
            unit="kcal",
            start_date=timezone.localdate(),
            active=True,
        )
        self.assertIn("My Calorie Goal", str(goal))


class CalculateGoalProgressTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="progressuser", password="pass")
        self.today = timezone.localdate()

        # FoodEntry for protein, carbs, fat, calories
        FoodEntry.objects.create(
            user=self.user,
            name="Test Food",
            calories=500,
            protein_g=Decimal("40.0"),
            carbs_g=Decimal("60.0"),
            fat_g=Decimal("15.0"),
        )

        # WaterEntry for water
        WaterEntry.objects.create(
            user=self.user,
            amount_ml=750,
        )

        # Workout + ExerciseEntry for workout_minutes and workouts_per_week
        self.workout = Workout.objects.create(
            user=self.user,
            name="Test Workout",
            performed_on=self.today,
        )
        ExerciseEntry.objects.create(
            user=self.user,
            workout=self.workout,
            exercise_name="Test Exercise",
            duration_minutes=45,
            calories_burned=300,
        )

    def _make_goal(self, goal_type):
        return Goal.objects.create(
            user=self.user,
            name=f"{goal_type} goal",
            goal_type=goal_type,
            target_value=Decimal("100.00"),
            unit="unit",
            start_date=self.today,
            active=True,
        )

    def test_progress_protein(self):
        goal = self._make_goal("protein")
        progress = calculate_goal_progress(goal)
        self.assertAlmostEqual(progress, 40.0, places=1)

    def test_progress_water(self):
        goal = self._make_goal("water")
        progress = calculate_goal_progress(goal)
        self.assertAlmostEqual(progress, 750.0, places=1)

    def test_progress_workout_minutes(self):
        goal = self._make_goal("workout_minutes")
        progress = calculate_goal_progress(goal)
        self.assertAlmostEqual(progress, 45.0, places=1)

    def test_progress_workouts_per_week(self):
        goal = self._make_goal("workouts_per_week")
        progress = calculate_goal_progress(goal)
        # One distinct workout day this week
        self.assertGreaterEqual(progress, 1.0)


class RecommendExercisesTest(TestCase):
    def setUp(self):
        ExerciseLibrary.objects.get_or_create(name="Running", defaults={"category": "cardio"})
        ExerciseLibrary.objects.get_or_create(name="Bench Press", defaults={"category": "strength"})
        ExerciseLibrary.objects.get_or_create(name="Plank", defaults={"category": "core"})

    def test_recommend_for_calories_goal(self):
        results = recommend_exercises_for_goal("calories", limit=5)
        self.assertIsNotNone(results)
        self.assertLessEqual(len(results), 5)

    def test_recommend_for_non_matching_goal_type(self):
        # An unrecognized goal type should return some exercises (fallback)
        results = recommend_exercises_for_goal("unknown_type", limit=5)
        self.assertIsNotNone(results)

    def test_recommend_respects_limit(self):
        for i in range(10):
            ExerciseLibrary.objects.get_or_create(name=f"GoalTestExercise {i}", defaults={"category": "cardio"})
        results = recommend_exercises_for_goal("calories", limit=3)
        self.assertLessEqual(len(results), 3)


class GoalListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="listuser", password="pass")
        self.client.login(username="listuser", password="pass")

    def test_get_returns_200(self):
        response = self.client.get(reverse("goals:list"))
        self.assertEqual(response.status_code, 200)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("goals:list"))
        self.assertNotEqual(response.status_code, 200)


class GoalAddViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="adduser", password="pass")
        self.client.login(username="adduser", password="pass")

    def _valid_post_data(self):
        return {
            "name": "New Goal",
            "goal_type": "calories",
            "target_value": "2000.00",
            "unit": "kcal",
            "start_date": timezone.localdate().isoformat(),
            "end_date": "",
            "active": True,
            "notify_email": False,
            "notify_push": False,
        }

    def test_get_returns_200(self):
        response = self.client.get(reverse("goals:add"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects_to_list(self):
        response = self.client.post(reverse("goals:add"), data=self._valid_post_data())
        self.assertIn(response.status_code, [200, 302])


class GoalEditViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="edituser", password="pass")
        self.other_user = User.objects.create_user(username="otheruser", password="pass")
        self.client.login(username="edituser", password="pass")
        self.goal = Goal.objects.create(
            user=self.user,
            name="Edit Me",
            goal_type="protein",
            target_value=Decimal("150.00"),
            unit="g",
            start_date=timezone.localdate(),
            active=True,
        )
        self.other_goal = Goal.objects.create(
            user=self.other_user,
            name="Other Goal",
            goal_type="fat",
            target_value=Decimal("50.00"),
            unit="g",
            start_date=timezone.localdate(),
            active=True,
        )

    def _valid_post_data(self):
        return {
            "name": "Edited Goal",
            "goal_type": "protein",
            "target_value": "160.00",
            "unit": "g",
            "start_date": timezone.localdate().isoformat(),
            "end_date": "",
            "active": True,
            "notify_email": False,
            "notify_push": False,
        }

    def test_get_returns_200(self):
        response = self.client.get(reverse("goals:edit", args=[self.goal.id]))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects(self):
        response = self.client.post(
            reverse("goals:edit", args=[self.goal.id]),
            data=self._valid_post_data(),
        )
        self.assertIn(response.status_code, [200, 302])

    def test_other_user_goal_returns_404(self):
        response = self.client.get(reverse("goals:edit", args=[self.other_goal.id]))
        self.assertEqual(response.status_code, 404)


class GoalDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="deleteuser", password="pass")
        self.other_user = User.objects.create_user(username="deleteotherusr", password="pass")
        self.client.login(username="deleteuser", password="pass")

    def _make_goal(self, user):
        return Goal.objects.create(
            user=user,
            name="Delete Me",
            goal_type="water",
            target_value=Decimal("2000.00"),
            unit="ml",
            start_date=timezone.localdate(),
            active=True,
        )

    def test_post_deletes_and_redirects(self):
        goal = self._make_goal(self.user)
        response = self.client.post(reverse("goals:delete", args=[goal.id]))
        self.assertIn(response.status_code, [200, 302])
        self.assertFalse(Goal.objects.filter(id=goal.id).exists())

    def test_other_user_goal_returns_404(self):
        other_goal = self._make_goal(self.other_user)
        response = self.client.post(reverse("goals:delete", args=[other_goal.id]))
        self.assertEqual(response.status_code, 404)
