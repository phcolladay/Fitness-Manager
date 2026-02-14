from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.nutrition.models import FoodEntry

from .models import Goal
from .services import calculate_goal_progress


class GoalProgressTests(TestCase):
    def test_calorie_goal_progress(self):
        user = get_user_model().objects.create_user(username="u1", password="pw")
        Goal.objects.create(
            name="Calories",
            goal_type="calories",
            target_value=2000,
            unit="kcal",
            user=user,
        )
        FoodEntry.objects.create(name="Test Meal", calories=500, user=user)
        goal = Goal.objects.get(name="Calories", user=user)

        progress = calculate_goal_progress(goal)
        self.assertEqual(progress, 500.0)

# Create your tests here.
