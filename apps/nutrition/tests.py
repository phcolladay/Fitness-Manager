from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import FoodEntry, WaterEntry


class NutritionModelTests(TestCase):
    def test_food_and_water_str(self):
        user = get_user_model().objects.create_user(username="u1", password="pw")
        food = FoodEntry.objects.create(name="Apple", calories=95, user=user)
        water = WaterEntry.objects.create(amount_ml=250, user=user)

        self.assertIn("Apple", str(food))
        self.assertIn("250", str(water))

# Create your tests here.
