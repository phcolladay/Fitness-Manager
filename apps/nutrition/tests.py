import os
import tempfile
from unittest.mock import Mock, patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import FoodEntry, WaterEntry
from .services import search_usda_foods
from .vision import recognize_food


class NutritionModelTests(TestCase):
    def test_food_and_water_str(self):
        user = get_user_model().objects.create_user(username="u1", password="pw")
        food = FoodEntry.objects.create(name="Apple", calories=95, user=user)
        water = WaterEntry.objects.create(amount_ml=250, user=user)

        self.assertIn("Apple", str(food))
        self.assertIn("250", str(water))


class NutritionServiceTests(TestCase):
    def test_usda_lookup_returns_empty_without_key(self):
        with patch.dict(os.environ, {"USDA_API_KEY": ""}, clear=False):
            self.assertEqual(search_usda_foods("banana"), [])

    def test_openai_recognize_requires_api_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                recognize_food("does-not-matter.jpg")

    def test_openai_recognize_parses_json_object(self):
        # Create a tiny temp image for the JPEG conversion step.
        from PIL import Image

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = tmp.name
        try:
            img = Image.new("RGB", (10, 10), color=(255, 0, 0))
            img.save(path, format="PNG")

            fake_response = Mock()
            fake_response.raise_for_status.return_value = None
            fake_response.headers = {}
            fake_response.status_code = 200
            fake_response.text = ""
            fake_response.json.return_value = {
                "output": [
                    {
                        "content": [
                            {
                                "text": (
                                    '{"name":"banana","calories":105,"protein_g":1.3,"carbs_g":27,'
                                    '"fat_g":0.3,"fiber_g":3.1,"sugar_g":14,"sodium_mg":1}'
                                )
                            }
                        ]
                    }
                ]
            }

            with patch.dict(os.environ, {"OPENAI_API_KEY": "test", "OPENAI_MODEL": "gpt-4.1-mini"}, clear=False):
                with patch("apps.nutrition.vision.requests.post", return_value=fake_response) as post:
                    result = recognize_food(path)

            self.assertEqual(result["name"], "banana")
            self.assertEqual(result["calories"], 105)
            post.assert_called_once()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
