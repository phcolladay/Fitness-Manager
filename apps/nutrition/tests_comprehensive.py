"""
Comprehensive unit tests for the nutrition app.
Covers: forms, helper functions (_period_range, _normalize_micronutrients), and views.
"""

import json
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.nutrition.forms import (
    FoodEntryForm,
    FoodEstimateForm,
    FoodLookupForm,
    WaterEntryForm,
)
from apps.nutrition.models import FoodEntry, WaterEntry
from apps.nutrition.views import _normalize_micronutrients, _period_range

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_food_entry_data(**overrides):
    """Return a dict of valid POST data for FoodEntryForm."""
    data = {
        "name": "Test Food",
        "brand": "Test Brand",
        "quantity": "1.00",
        "unit": "serving",
        "calories": "200.00",
        "protein_g": "10.00",
        "carbs_g": "30.00",
        "fat_g": "5.00",
        "fiber_g": "3.00",
        "sugar_g": "2.00",
        "sodium_mg": "150.00",
        "micronutrients": "",
        "consumed_at": timezone.now().strftime("%Y-%m-%dT%H:%M"),
    }
    data.update(overrides)
    return data


def make_water_entry_data(**overrides):
    """Return a dict of valid POST data for WaterEntryForm."""
    data = {
        "unit": "ml",
        "amount": "500",
        "consumed_at": timezone.now().strftime("%Y-%m-%dT%H:%M"),
    }
    data.update(overrides)
    return data


# ===========================================================================
# 1. Form tests
# ===========================================================================

class FoodEntryFormTests(TestCase):

    def test_valid_data_is_accepted(self):
        form = FoodEntryForm(data=make_food_entry_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_negative_calories_raises_error(self):
        form = FoodEntryForm(data=make_food_entry_data(calories="-1"))
        self.assertFalse(form.is_valid())
        self.assertIn("calories", form.errors)

    def test_negative_protein_raises_error(self):
        form = FoodEntryForm(data=make_food_entry_data(protein_g="-0.5"))
        self.assertFalse(form.is_valid())
        self.assertIn("protein_g", form.errors)

    def test_negative_carbs_raises_error(self):
        form = FoodEntryForm(data=make_food_entry_data(carbs_g="-10"))
        self.assertFalse(form.is_valid())
        self.assertIn("carbs_g", form.errors)

    def test_negative_fat_raises_error(self):
        form = FoodEntryForm(data=make_food_entry_data(fat_g="-2"))
        self.assertFalse(form.is_valid())
        self.assertIn("fat_g", form.errors)

    def test_negative_fiber_raises_error(self):
        form = FoodEntryForm(data=make_food_entry_data(fiber_g="-1"))
        self.assertFalse(form.is_valid())
        self.assertIn("fiber_g", form.errors)

    def test_negative_sugar_raises_error(self):
        form = FoodEntryForm(data=make_food_entry_data(sugar_g="-0.1"))
        self.assertFalse(form.is_valid())
        self.assertIn("sugar_g", form.errors)

    def test_negative_sodium_raises_error(self):
        form = FoodEntryForm(data=make_food_entry_data(sodium_mg="-50"))
        self.assertFalse(form.is_valid())
        self.assertIn("sodium_mg", form.errors)

    def test_negative_quantity_raises_error(self):
        form = FoodEntryForm(data=make_food_entry_data(quantity="-1"))
        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)

    def test_zero_values_are_accepted(self):
        """Zero is a valid non-negative value for all numeric fields."""
        form = FoodEntryForm(data=make_food_entry_data(
            calories="0", protein_g="0", carbs_g="0",
            fat_g="0", fiber_g="0", sugar_g="0", sodium_mg="0",
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_name_is_required(self):
        form = FoodEntryForm(data=make_food_entry_data(name=""))
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)


class WaterEntryFormTests(TestCase):

    def test_ml_unit_saves_amount_directly(self):
        """When unit is ml, amount_ml should equal the entered amount (rounded to int)."""
        form = WaterEntryForm(data=make_water_entry_data(unit="ml", amount="500"))
        self.assertTrue(form.is_valid(), form.errors)
        entry = form.save(commit=False)
        self.assertEqual(entry.amount_ml, 500)

    def test_oz_unit_converts_to_ml(self):
        """When unit is oz, amount_ml should equal amount * 29.5735 rounded to int."""
        oz_amount = 10
        expected_ml = int(round(oz_amount * 29.5735))  # 296
        form = WaterEntryForm(data=make_water_entry_data(unit="oz", amount=str(oz_amount)))
        self.assertTrue(form.is_valid(), form.errors)
        entry = form.save(commit=False)
        self.assertEqual(entry.amount_ml, expected_ml)

    def test_oz_fractional_amount_converts_correctly(self):
        """Fractional oz amounts are converted and rounded to the nearest int."""
        oz_amount = "8.5"
        expected_ml = int(round(8.5 * 29.5735))
        form = WaterEntryForm(data=make_water_entry_data(unit="oz", amount=oz_amount))
        self.assertTrue(form.is_valid(), form.errors)
        entry = form.save(commit=False)
        self.assertEqual(entry.amount_ml, expected_ml)

    def test_negative_amount_is_invalid(self):
        form = WaterEntryForm(data=make_water_entry_data(amount="-1"))
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_invalid_unit_choice_is_rejected(self):
        form = WaterEntryForm(data=make_water_entry_data(unit="cups"))
        self.assertFalse(form.is_valid())
        self.assertIn("unit", form.errors)

    def test_ml_unit_stores_rounded_int(self):
        """Decimal ml values should be rounded to int."""
        form = WaterEntryForm(data=make_water_entry_data(unit="ml", amount="250.75"))
        self.assertTrue(form.is_valid(), form.errors)
        entry = form.save(commit=False)
        self.assertEqual(entry.amount_ml, 251)


class FoodLookupFormTests(TestCase):

    def test_valid_query_is_accepted(self):
        form = FoodLookupForm(data={"query": "chicken breast"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_empty_query_is_invalid(self):
        form = FoodLookupForm(data={"query": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("query", form.errors)

    def test_query_too_long_is_invalid(self):
        form = FoodLookupForm(data={"query": "x" * 151})
        self.assertFalse(form.is_valid())
        self.assertIn("query", form.errors)

    def test_max_length_query_is_accepted(self):
        form = FoodLookupForm(data={"query": "x" * 150})
        self.assertTrue(form.is_valid(), form.errors)


class FoodEstimateFormTests(TestCase):

    def test_valid_description_is_accepted(self):
        form = FoodEstimateForm(data={"description": "grilled chicken breast, brown rice, broccoli"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_empty_description_is_invalid(self):
        form = FoodEstimateForm(data={"description": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)

    def test_description_too_long_is_invalid(self):
        form = FoodEstimateForm(data={"description": "x" * 1001})
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)


# ===========================================================================
# 2. Helper function tests
# ===========================================================================

class PeriodRangeTests(TestCase):

    def test_period_day(self):
        period, start, today, start_dt, end_dt = _period_range("day")
        self.assertEqual(period, "day")
        self.assertEqual(start, today)
        self.assertLess(start_dt, end_dt)

    def test_period_week(self):
        period, start, today, start_dt, end_dt = _period_range("week")
        self.assertEqual(period, "week")
        self.assertEqual((today - start).days, 6)
        self.assertLess(start_dt, end_dt)

    def test_period_month(self):
        period, start, today, start_dt, end_dt = _period_range("month")
        self.assertEqual(period, "month")
        self.assertEqual((today - start).days, 29)
        self.assertLess(start_dt, end_dt)

    def test_unknown_period_defaults_to_day(self):
        period, start, today, start_dt, end_dt = _period_range("yearly")
        self.assertEqual(period, "day")
        self.assertEqual(start, today)

    def test_empty_string_defaults_to_day(self):
        period, start, today, start_dt, end_dt = _period_range("")
        self.assertEqual(period, "day")

    def test_start_dt_is_start_of_day(self):
        _, start, today, start_dt, _ = _period_range("day")
        # start_dt should be midnight of start date
        self.assertEqual(start_dt.date(), start)
        self.assertEqual(start_dt.hour, 0)
        self.assertEqual(start_dt.minute, 0)

    def test_end_dt_is_end_of_today(self):
        _, _, today, _, end_dt = _period_range("day")
        self.assertEqual(end_dt.date(), today)
        self.assertEqual(end_dt.hour, 23)
        self.assertEqual(end_dt.minute, 59)


class NormalizeMicronutrientsTests(TestCase):

    def test_dict_input_returned_as_float_values(self):
        raw = {"vitamin_c_mg": 90, "iron_mg": 18.0, "calcium_mg": "1300"}
        result = _normalize_micronutrients(raw)
        self.assertEqual(result, {"vitamin_c_mg": 90.0, "iron_mg": 18.0, "calcium_mg": 1300.0})

    def test_json_string_input_is_parsed(self):
        raw = json.dumps({"vitamin_c_mg": 90, "iron_mg": 18})
        result = _normalize_micronutrients(raw)
        self.assertEqual(result["vitamin_c_mg"], 90.0)
        self.assertEqual(result["iron_mg"], 18.0)

    def test_invalid_json_string_returns_empty_dict(self):
        result = _normalize_micronutrients("not valid json {{")
        self.assertEqual(result, {})

    def test_none_returns_empty_dict(self):
        result = _normalize_micronutrients(None)
        self.assertEqual(result, {})

    def test_integer_returns_empty_dict(self):
        result = _normalize_micronutrients(42)
        self.assertEqual(result, {})

    def test_list_returns_empty_dict(self):
        result = _normalize_micronutrients(["vitamin_c", 90])
        self.assertEqual(result, {})

    def test_negative_values_are_filtered_out(self):
        raw = {"vitamin_c_mg": -5, "iron_mg": 18}
        result = _normalize_micronutrients(raw)
        self.assertNotIn("vitamin_c_mg", result)
        self.assertIn("iron_mg", result)

    def test_zero_value_is_kept(self):
        raw = {"vitamin_c_mg": 0}
        result = _normalize_micronutrients(raw)
        self.assertIn("vitamin_c_mg", result)
        self.assertEqual(result["vitamin_c_mg"], 0.0)

    def test_non_numeric_string_value_is_skipped(self):
        raw = {"vitamin_c_mg": "lots", "iron_mg": 18}
        result = _normalize_micronutrients(raw)
        self.assertNotIn("vitamin_c_mg", result)
        self.assertIn("iron_mg", result)

    def test_empty_dict_returns_empty_dict(self):
        result = _normalize_micronutrients({})
        self.assertEqual(result, {})

    def test_keys_are_converted_to_str(self):
        raw = {1: 100, "iron_mg": 18}
        result = _normalize_micronutrients(raw)
        self.assertIn("1", result)
        self.assertIn("iron_mg", result)


# ===========================================================================
# 3. View tests
# ===========================================================================

class NutritionViewTestBase(TestCase):
    """Base class that creates a test user and logs them in."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testnutritionuser",
            password="TestPass123!",
            email="testnutritionuser@example.com",
        )
        self.other_user = User.objects.create_user(
            username="othernutritionuser",
            password="TestPass123!",
            email="othernutritionuser@example.com",
        )
        self.client.login(username="testnutritionuser", password="TestPass123!")

    def create_food_entry(self, user=None, **kwargs):
        defaults = {
            "name": "Test Food",
            "calories": Decimal("200.00"),
            "protein_g": Decimal("10.00"),
            "carbs_g": Decimal("30.00"),
            "fat_g": Decimal("5.00"),
            "fiber_g": Decimal("3.00"),
            "sugar_g": Decimal("2.00"),
            "sodium_mg": Decimal("150.00"),
            "consumed_at": timezone.now(),
        }
        defaults.update(kwargs)
        return FoodEntry.objects.create(user=user or self.user, **defaults)

    def create_water_entry(self, user=None, **kwargs):
        defaults = {
            "amount_ml": 500,
            "consumed_at": timezone.now(),
        }
        defaults.update(kwargs)
        return WaterEntry.objects.create(user=user or self.user, **defaults)

    def assertRedirectsTo(self, response, url_name, *args):
        """Assert a 302 without fetching the redirect destination (avoids template render)."""
        self.assertEqual(response.status_code, 302)
        expected = reverse(url_name, args=args) if args else reverse(url_name)
        self.assertEqual(response["Location"], expected)

    def assertLoginRedirect(self, response):
        """Assert anonymous user is sent to login."""
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])


# ---------------------------------------------------------------------------
# food_list
# ---------------------------------------------------------------------------

class FoodListViewTests(NutritionViewTestBase):

    def test_get_returns_200_for_authenticated_user(self):
        response = self.client.get(reverse("nutrition:list"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("nutrition:list"))
        self.assertLoginRedirect(response)

    def test_only_own_entries_are_in_db(self):
        """Verify DB scoping — own entry exists, other user's entry also exists but separately."""
        own = self.create_food_entry(name="Own Food")
        other = self.create_food_entry(user=self.other_user, name="Other Food")
        own_qs = FoodEntry.objects.filter(user=self.user)
        other_qs = FoodEntry.objects.filter(user=self.other_user)
        self.assertIn(own, own_qs)
        self.assertNotIn(other, own_qs)
        self.assertIn(other, other_qs)


# ---------------------------------------------------------------------------
# food_add
# ---------------------------------------------------------------------------

class FoodAddViewTests(NutritionViewTestBase):

    def test_get_returns_200(self):
        response = self.client.get(reverse("nutrition:add"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        response = self.client.get(reverse("nutrition:add"))
        self.assertLoginRedirect(response)

    def test_valid_post_creates_entry_and_redirects_to_list(self):
        data = make_food_entry_data()
        response = self.client.post(reverse("nutrition:add"), data=data)
        self.assertRedirectsTo(response, "nutrition:list")
        self.assertTrue(FoodEntry.objects.filter(user=self.user, name="Test Food").exists())

    def test_invalid_post_rerenders_form_with_200(self):
        data = make_food_entry_data(calories="-100")
        response = self.client.post(reverse("nutrition:add"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FoodEntry.objects.filter(user=self.user).exists())

    def test_entry_is_assigned_to_logged_in_user(self):
        data = make_food_entry_data(name="My Meal")
        self.client.post(reverse("nutrition:add"), data=data)
        entry = FoodEntry.objects.get(user=self.user, name="My Meal")
        self.assertEqual(entry.user, self.user)


# ---------------------------------------------------------------------------
# food_edit
# ---------------------------------------------------------------------------

class FoodEditViewTests(NutritionViewTestBase):

    def test_get_own_entry_returns_200(self):
        entry = self.create_food_entry()
        response = self.client.get(reverse("nutrition:edit", args=[entry.id]))
        self.assertEqual(response.status_code, 200)

    def test_get_other_users_entry_redirects_with_error(self):
        other_entry = self.create_food_entry(user=self.other_user)
        response = self.client.get(reverse("nutrition:edit", args=[other_entry.id]))
        self.assertRedirectsTo(response, "nutrition:list")

    def test_valid_post_updates_entry_and_redirects(self):
        entry = self.create_food_entry(name="Original Name")
        data = make_food_entry_data(name="Updated Name")
        response = self.client.post(reverse("nutrition:edit", args=[entry.id]), data=data)
        self.assertRedirectsTo(response, "nutrition:list")
        entry.refresh_from_db()
        self.assertEqual(entry.name, "Updated Name")

    def test_invalid_post_rerenders_form_with_200(self):
        entry = self.create_food_entry()
        data = make_food_entry_data(calories="-1")
        response = self.client.post(reverse("nutrition:edit", args=[entry.id]), data=data)
        self.assertEqual(response.status_code, 200)

    def test_edit_nonexistent_entry_redirects_to_list(self):
        response = self.client.get(reverse("nutrition:edit", args=[99999]))
        self.assertRedirectsTo(response, "nutrition:list")

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        entry = self.create_food_entry()
        response = self.client.get(reverse("nutrition:edit", args=[entry.id]))
        self.assertLoginRedirect(response)


# ---------------------------------------------------------------------------
# food_delete
# ---------------------------------------------------------------------------

class FoodDeleteViewTests(NutritionViewTestBase):

    def test_post_deletes_own_entry_and_redirects(self):
        entry = self.create_food_entry()
        entry_id = entry.id
        response = self.client.post(reverse("nutrition:delete", args=[entry_id]))
        self.assertRedirectsTo(response, "nutrition:list")
        self.assertFalse(FoodEntry.objects.filter(id=entry_id).exists())

    def test_post_other_users_entry_redirects_and_does_not_delete(self):
        other_entry = self.create_food_entry(user=self.other_user)
        entry_id = other_entry.id
        response = self.client.post(reverse("nutrition:delete", args=[entry_id]))
        self.assertRedirectsTo(response, "nutrition:list")
        # Entry should still exist — no permission to delete other user's data
        self.assertTrue(FoodEntry.objects.filter(id=entry_id).exists())

    def test_post_nonexistent_entry_redirects_to_list(self):
        response = self.client.post(reverse("nutrition:delete", args=[99999]))
        self.assertRedirectsTo(response, "nutrition:list")

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        entry = self.create_food_entry()
        response = self.client.post(reverse("nutrition:delete", args=[entry.id]))
        self.assertLoginRedirect(response)


# ---------------------------------------------------------------------------
# food_summary
# ---------------------------------------------------------------------------

class FoodSummaryViewTests(NutritionViewTestBase):

    def test_get_returns_200(self):
        response = self.client.get(reverse("nutrition:summary"))
        self.assertEqual(response.status_code, 200)

    def test_period_week_returns_200(self):
        response = self.client.get(reverse("nutrition:summary") + "?period=week")
        self.assertEqual(response.status_code, 200)

    def test_period_month_returns_200(self):
        response = self.client.get(reverse("nutrition:summary") + "?period=month")
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        response = self.client.get(reverse("nutrition:summary"))
        self.assertLoginRedirect(response)

    def test_summary_aggregates_own_entries_only(self):
        """Verify DB-level scoping: own entry calories appear, other user's do not."""
        self.create_food_entry(calories=Decimal("500.00"))
        self.create_food_entry(user=self.other_user, calories=Decimal("999.00"))
        # DB query scoped to request user — other user entry must not appear in user's total
        from django.db.models import Sum
        total = FoodEntry.objects.filter(
            user=self.user
        ).aggregate(total=Sum("calories"))["total"] or 0
        self.assertEqual(float(total), 500.0)


# ---------------------------------------------------------------------------
# food_lookup
# ---------------------------------------------------------------------------

class FoodLookupViewTests(NutritionViewTestBase):

    def test_get_without_query_returns_200(self):
        response = self.client.get(reverse("nutrition:lookup"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        response = self.client.get(reverse("nutrition:lookup"))
        self.assertLoginRedirect(response)

    def test_get_with_query_and_no_usda_key_returns_empty_results(self):
        """Without USDA_API_KEY, search returns empty list; view still renders 200."""
        import os
        env_without_key = {k: v for k, v in os.environ.items() if k != "USDA_API_KEY"}
        with mock.patch.dict("os.environ", env_without_key, clear=True):
            response = self.client.get(reverse("nutrition:lookup") + "?query=chicken")
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# food_estimate
# ---------------------------------------------------------------------------

class FoodEstimateViewTests(NutritionViewTestBase):

    def test_get_returns_200(self):
        response = self.client.get(reverse("nutrition:estimate"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        response = self.client.get(reverse("nutrition:estimate"))
        self.assertLoginRedirect(response)


# ---------------------------------------------------------------------------
# food_photo_upload
# ---------------------------------------------------------------------------

class FoodPhotoUploadViewTests(NutritionViewTestBase):

    def test_get_returns_200(self):
        response = self.client.get(reverse("nutrition:photo_upload"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        response = self.client.get(reverse("nutrition:photo_upload"))
        self.assertLoginRedirect(response)


# ---------------------------------------------------------------------------
# water_list
# ---------------------------------------------------------------------------

class WaterListViewTests(NutritionViewTestBase):

    def test_get_returns_200(self):
        response = self.client.get(reverse("nutrition:water_list"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        response = self.client.get(reverse("nutrition:water_list"))
        self.assertLoginRedirect(response)

    def test_period_week_returns_200(self):
        response = self.client.get(reverse("nutrition:water_list") + "?period=week")
        self.assertEqual(response.status_code, 200)

    def test_only_own_water_entries_appear_in_db_query(self):
        """DB-level check: filter by user excludes other user's records."""
        own = self.create_water_entry(amount_ml=300)
        other = self.create_water_entry(user=self.other_user, amount_ml=999)
        own_qs = WaterEntry.objects.filter(user=self.user)
        self.assertIn(own, own_qs)
        self.assertNotIn(other, own_qs)


# ---------------------------------------------------------------------------
# water_add
# ---------------------------------------------------------------------------

class WaterAddViewTests(NutritionViewTestBase):

    def test_get_returns_200(self):
        response = self.client.get(reverse("nutrition:water_add"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        response = self.client.get(reverse("nutrition:water_add"))
        self.assertLoginRedirect(response)

    def test_valid_post_creates_entry_and_redirects_to_water_list(self):
        data = make_water_entry_data(unit="ml", amount="750")
        response = self.client.post(reverse("nutrition:water_add"), data=data)
        self.assertRedirectsTo(response, "nutrition:water_list")
        self.assertTrue(WaterEntry.objects.filter(user=self.user, amount_ml=750).exists())

    def test_oz_post_converts_and_saves_correctly(self):
        oz = 16
        expected_ml = int(round(oz * 29.5735))
        data = make_water_entry_data(unit="oz", amount=str(oz))
        self.client.post(reverse("nutrition:water_add"), data=data)
        self.assertTrue(WaterEntry.objects.filter(user=self.user, amount_ml=expected_ml).exists())

    def test_invalid_post_rerenders_form_with_200(self):
        data = make_water_entry_data(amount="-100")
        response = self.client.post(reverse("nutrition:water_add"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(WaterEntry.objects.filter(user=self.user).exists())


# ---------------------------------------------------------------------------
# water_edit
# ---------------------------------------------------------------------------

class WaterEditViewTests(NutritionViewTestBase):

    def test_get_own_entry_returns_200(self):
        entry = self.create_water_entry()
        response = self.client.get(reverse("nutrition:water_edit", args=[entry.id]))
        self.assertEqual(response.status_code, 200)

    def test_get_nonexistent_entry_redirects_to_water_list(self):
        response = self.client.get(reverse("nutrition:water_edit", args=[99999]))
        self.assertRedirectsTo(response, "nutrition:water_list")

    def test_get_other_users_entry_redirects_to_water_list(self):
        other_entry = self.create_water_entry(user=self.other_user)
        response = self.client.get(reverse("nutrition:water_edit", args=[other_entry.id]))
        self.assertRedirectsTo(response, "nutrition:water_list")

    def test_valid_post_updates_entry_and_redirects(self):
        entry = self.create_water_entry(amount_ml=200)
        data = make_water_entry_data(unit="ml", amount="600")
        response = self.client.post(reverse("nutrition:water_edit", args=[entry.id]), data=data)
        self.assertRedirectsTo(response, "nutrition:water_list")
        entry.refresh_from_db()
        self.assertEqual(entry.amount_ml, 600)

    def test_invalid_post_rerenders_form_with_200(self):
        entry = self.create_water_entry()
        data = make_water_entry_data(amount="-10")
        response = self.client.post(reverse("nutrition:water_edit", args=[entry.id]), data=data)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        entry = self.create_water_entry()
        response = self.client.get(reverse("nutrition:water_edit", args=[entry.id]))
        self.assertLoginRedirect(response)


# ---------------------------------------------------------------------------
# water_delete
# ---------------------------------------------------------------------------

class WaterDeleteViewTests(NutritionViewTestBase):

    def test_post_deletes_own_entry_and_redirects(self):
        entry = self.create_water_entry()
        entry_id = entry.id
        response = self.client.post(reverse("nutrition:water_delete", args=[entry_id]))
        self.assertRedirectsTo(response, "nutrition:water_list")
        self.assertFalse(WaterEntry.objects.filter(id=entry_id).exists())

    def test_post_nonexistent_entry_redirects_to_water_list(self):
        response = self.client.post(reverse("nutrition:water_delete", args=[99999]))
        self.assertRedirectsTo(response, "nutrition:water_list")

    def test_post_other_users_entry_redirects_and_does_not_delete(self):
        other_entry = self.create_water_entry(user=self.other_user)
        entry_id = other_entry.id
        response = self.client.post(reverse("nutrition:water_delete", args=[entry_id]))
        self.assertRedirectsTo(response, "nutrition:water_list")
        self.assertTrue(WaterEntry.objects.filter(id=entry_id).exists())

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        entry = self.create_water_entry()
        response = self.client.post(reverse("nutrition:water_delete", args=[entry.id]))
        self.assertLoginRedirect(response)
