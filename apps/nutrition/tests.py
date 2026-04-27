import os
import tempfile
import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock, patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import FoodEntry, WaterEntry
from .services import _extract_nutrients, search_usda_foods
from .views import _prefill_add_url
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

    def test_extract_nutrients_includes_micros(self):
        nutrients = [
            {"nutrientName": "Iron, Fe", "value": 2.7, "unitName": "mg"},
            {"nutrientName": "Calcium, Ca", "value": 220, "unitName": "mg"},
            {"nutrientName": "Vitamin C, total ascorbic acid", "value": 12, "unitName": "mg"},
            {"nutrientName": "Fiber, total dietary", "value": 3.1, "unitName": "g"},
            {"nutrientName": "Sodium, Na", "value": 45, "unitName": "mg"},
        ]
        mapped = _extract_nutrients(nutrients)
        micros = mapped.get("micronutrients", {})
        self.assertEqual(micros.get("iron_mg"), 2.7)
        self.assertEqual(micros.get("calcium_mg"), 220.0)
        self.assertEqual(micros.get("vitamin_c_mg"), 12.0)
        self.assertEqual(micros.get("fiber_g"), 3.1)
        self.assertEqual(micros.get("sodium_mg"), 45.0)

    def test_prefill_url_serializes_micronutrients(self):
        url = _prefill_add_url(
            source="manual",
            result={
                "name": "Banana bowl",
                "calories": 320,
                "protein_g": 9,
                "carbs_g": 58,
                "fat_g": 7,
                "fiber_g": 8,
                "sodium_mg": 120,
                "micronutrients": {"iron_mg": 1.8, "calcium_mg": "42"},
            },
            default_name="Estimated meal",
        )
        query = parse_qs(urlparse(url).query)
        payload = json.loads(query["micronutrients"][0])
        self.assertEqual(payload["iron_mg"], 1.8)
        self.assertEqual(payload["calcium_mg"], 42.0)
        self.assertEqual(payload["fiber_g"], 8.0)
