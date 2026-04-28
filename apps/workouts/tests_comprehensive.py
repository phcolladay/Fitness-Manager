"""
Comprehensive unit tests for the workouts app.

Covers:
  - apps.workouts.utils  (classify_exercise, estimate_calories)
  - apps.workouts.ai     (_extract_output_text, _coerce_json_object,
                          estimate_exercise_calories_ai)
  - apps.workouts.forms  (WorkoutForm, ExerciseEntryForm, WorkoutPlanForm)
  - apps.workouts.views  (all URL-backed views + _workout_period helper)
"""

import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.workouts.ai import _coerce_json_object, _extract_output_text, estimate_exercise_calories_ai
from apps.workouts.forms import ExerciseEntryForm, WorkoutForm, WorkoutPlanForm
from apps.workouts.models import ExerciseEntry, ExerciseLibrary, Workout, WorkoutPlan
from apps.workouts.utils import classify_exercise, estimate_calories
from apps.workouts.views import _workout_period

User = get_user_model()


# ---------------------------------------------------------------------------
# 1. Utils
# ---------------------------------------------------------------------------

class ClassifyExerciseTests(TestCase):
    """Tests for classify_exercise()."""

    def test_run_returns_cardio_legs(self):
        self.assertEqual(classify_exercise("morning run"), ("cardio", "legs"))

    def test_jog_returns_cardio_legs(self):
        self.assertEqual(classify_exercise("easy jog"), ("cardio", "legs"))

    def test_cycle_returns_cardio_legs(self):
        self.assertEqual(classify_exercise("cycle tour"), ("cardio", "legs"))

    def test_bike_returns_cardio_legs(self):
        self.assertEqual(classify_exercise("stationary bike"), ("cardio", "legs"))

    def test_swim_returns_cardio_full_body(self):
        self.assertEqual(classify_exercise("swim laps"), ("cardio", "full body"))

    def test_bench_returns_strength_chest(self):
        self.assertEqual(classify_exercise("bench press"), ("strength", "chest"))

    def test_push_returns_strength_chest(self):
        self.assertEqual(classify_exercise("push-ups"), ("strength", "chest"))

    def test_pull_returns_strength_back(self):
        self.assertEqual(classify_exercise("pull-ups"), ("strength", "back"))

    def test_row_returns_strength_back(self):
        self.assertEqual(classify_exercise("cable row"), ("strength", "back"))

    def test_squat_returns_strength_legs(self):
        self.assertEqual(classify_exercise("barbell squat"), ("strength", "legs"))

    def test_deadlift_returns_strength_back(self):
        self.assertEqual(classify_exercise("Romanian deadlift"), ("strength", "back"))

    def test_plank_returns_core_core(self):
        self.assertEqual(classify_exercise("plank hold"), ("core", "core"))

    def test_yoga_returns_mobility_full_body(self):
        self.assertEqual(classify_exercise("morning yoga"), ("mobility", "full body"))

    def test_unknown_name_returns_general_empty(self):
        self.assertEqual(classify_exercise("juggling"), ("general", ""))

    def test_case_insensitive_running(self):
        self.assertEqual(classify_exercise("RUNNING sprints"), ("cardio", "legs"))

    def test_case_insensitive_bench(self):
        self.assertEqual(classify_exercise("BENCH PRESS"), ("strength", "chest"))

    def test_mixed_case_yoga(self):
        self.assertEqual(classify_exercise("Evening YOGA Flow"), ("mobility", "full body"))


class EstimateCaloriesTests(TestCase):
    """Tests for estimate_calories()."""

    def test_cardio_calories(self):
        # 8.0 cal/min * 30 min = 240.0
        self.assertEqual(estimate_calories("cardio", 30), 240.0)

    def test_strength_calories(self):
        # 6.0 * 45 = 270.0
        self.assertEqual(estimate_calories("strength", 45), 270.0)

    def test_core_calories(self):
        # 5.0 * 20 = 100.0
        self.assertEqual(estimate_calories("core", 20), 100.0)

    def test_mobility_calories(self):
        # 3.0 * 60 = 180.0
        self.assertEqual(estimate_calories("mobility", 60), 180.0)

    def test_hiit_calories(self):
        # 10.0 * 12 = 120.0
        self.assertEqual(estimate_calories("hiit", 12), 120.0)

    def test_unknown_category_uses_default_5(self):
        # 5.0 * 10 = 50.0
        self.assertEqual(estimate_calories("general", 10), 50.0)

    def test_zero_duration_returns_zero(self):
        self.assertEqual(estimate_calories("cardio", 0), 0.0)

    def test_negative_duration_treated_as_zero(self):
        self.assertEqual(estimate_calories("cardio", -5), 0.0)

    def test_rounding(self):
        # 8.0 * 1 = 8.0 – trivial, but verifies return type is float
        result = estimate_calories("cardio", 1)
        self.assertIsInstance(result, float)


# ---------------------------------------------------------------------------
# 2. AI helpers
# ---------------------------------------------------------------------------

class ExtractOutputTextTests(TestCase):
    """Tests for _extract_output_text()."""

    def test_valid_nested_payload(self):
        payload = {
            "output": [
                {"content": [{"text": "  hello world  "}]},
            ]
        }
        self.assertEqual(_extract_output_text(payload), "  hello world  ")

    def test_multiple_output_items_returns_first_text(self):
        payload = {
            "output": [
                {"content": [{"text": "first"}]},
                {"content": [{"text": "second"}]},
            ]
        }
        self.assertEqual(_extract_output_text(payload), "first")

    def test_output_text_fallback(self):
        payload = {"output_text": "fallback text"}
        self.assertEqual(_extract_output_text(payload), "fallback text")

    def test_prefers_nested_over_output_text(self):
        payload = {
            "output": [{"content": [{"text": "nested"}]}],
            "output_text": "fallback",
        }
        self.assertEqual(_extract_output_text(payload), "nested")

    def test_empty_payload_raises_value_error(self):
        with self.assertRaises(ValueError):
            _extract_output_text({})

    def test_whitespace_only_text_is_skipped(self):
        payload = {
            "output": [{"content": [{"text": "   "}]}],
        }
        with self.assertRaises(ValueError):
            _extract_output_text(payload)

    def test_empty_output_list_with_output_text_fallback(self):
        payload = {"output": [], "output_text": "here"}
        self.assertEqual(_extract_output_text(payload), "here")

    def test_none_output_field_with_output_text_fallback(self):
        payload = {"output": None, "output_text": "ok"}
        self.assertEqual(_extract_output_text(payload), "ok")


class CoerceJsonObjectTests(TestCase):
    """Tests for _coerce_json_object()."""

    def test_valid_json_object(self):
        result = _coerce_json_object('{"calories_burned": 150, "reasoning_short": "est"}')
        self.assertEqual(result, {"calories_burned": 150, "reasoning_short": "est"})

    def test_json_embedded_in_text(self):
        text = 'Here is the result: {"calories_burned": 200} – enjoy!'
        result = _coerce_json_object(text)
        self.assertEqual(result, {"calories_burned": 200})

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            _coerce_json_object("")

    def test_whitespace_only_raises_value_error(self):
        with self.assertRaises(ValueError):
            _coerce_json_object("   ")

    def test_plain_invalid_json_raises_value_error(self):
        with self.assertRaises(ValueError):
            _coerce_json_object("not json at all")

    def test_json_array_raises_value_error(self):
        # A JSON array is not a dict – should raise
        with self.assertRaises(ValueError):
            _coerce_json_object("[1, 2, 3]")

    def test_nested_braces_returns_outer_object(self):
        # The function uses rfind("}") so it covers the full span
        text = '{"a": {"b": 1}}'
        result = _coerce_json_object(text)
        self.assertEqual(result, {"a": {"b": 1}})


class EstimateExerciseCaloriesAiTests(TestCase):
    """Tests for estimate_exercise_calories_ai()."""

    def test_returns_none_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            # Ensure OPENAI_API_KEY is absent
            import os
            os.environ.pop("OPENAI_API_KEY", None)
            result = estimate_exercise_calories_ai(
                exercise_name="running",
                duration_minutes=30,
            )
        self.assertIsNone(result)

    def test_returns_none_without_exercise_name(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}):
            result = estimate_exercise_calories_ai(
                exercise_name="",
                duration_minutes=30,
            )
        self.assertIsNone(result)

    def test_returns_none_without_duration(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}):
            result = estimate_exercise_calories_ai(
                exercise_name="running",
                duration_minutes=0,
            )
        self.assertIsNone(result)

    def test_returns_none_on_connection_error(self):
        """Network errors should be caught and return None."""
        import requests as req_lib
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}):
            with patch("apps.workouts.ai.requests.post", side_effect=req_lib.ConnectionError("no network")):
                result = estimate_exercise_calories_ai(
                    exercise_name="running",
                    duration_minutes=30,
                )
        self.assertIsNone(result)

    def test_returns_float_on_success(self):
        """Mock a successful API call and verify the parsed value is returned."""
        fake_payload = {
            "output": [
                {"content": [{"text": json.dumps({"calories_burned": 250.5, "reasoning_short": "ok"})}]}
            ]
        }
        mock_response = type("R", (), {
            "status_code": 200,
            "raise_for_status": lambda self: None,
            "json": lambda self: fake_payload,
        })()

        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}):
            with patch("apps.workouts.ai.requests.post", return_value=mock_response):
                result = estimate_exercise_calories_ai(
                    exercise_name="running",
                    duration_minutes=30,
                )
        self.assertEqual(result, 250.5)

    def test_returns_none_for_negative_calories_in_response(self):
        """If the AI returns a negative calories_burned, the function should return None."""
        fake_payload = {
            "output": [
                {"content": [{"text": json.dumps({"calories_burned": -10, "reasoning_short": "bad"})}]}
            ]
        }
        mock_response = type("R", (), {
            "status_code": 200,
            "raise_for_status": lambda self: None,
            "json": lambda self: fake_payload,
        })()

        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}):
            with patch("apps.workouts.ai.requests.post", return_value=mock_response):
                result = estimate_exercise_calories_ai(
                    exercise_name="running",
                    duration_minutes=30,
                )
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# 3. Forms
# ---------------------------------------------------------------------------

class WorkoutFormTests(TestCase):
    """Tests for WorkoutForm."""

    def _valid_data(self):
        return {
            "name": "Morning Run",
            "performed_on": "2026-04-14",
            "notes": "Felt great",
        }

    def test_valid_data_is_valid(self):
        form = WorkoutForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_name_is_invalid(self):
        data = self._valid_data()
        data["name"] = ""
        form = WorkoutForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_missing_performed_on_is_invalid(self):
        data = self._valid_data()
        data["performed_on"] = ""
        form = WorkoutForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("performed_on", form.errors)

    def test_notes_is_optional(self):
        data = self._valid_data()
        data["notes"] = ""
        form = WorkoutForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


class ExerciseEntryFormTests(TestCase):
    """Tests for ExerciseEntryForm."""

    def _valid_data(self):
        return {
            "exercise_name": "Bench Press",
            "category": "strength",
            "muscle_group": "chest",
            "duration_minutes": 30,
            "calories_burned": "150.00",
        }

    def test_valid_data_is_valid(self):
        form = ExerciseEntryForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_exercise_name_uses_library_dropdown(self):
        form = ExerciseEntryForm()
        self.assertEqual(form.fields["exercise_name"].widget.__class__.__name__, "Select")
        choices = {value for value, _label in form.fields["exercise_name"].choices}
        self.assertIn("Bench Press", choices)
        self.assertIn("Jump Squats", choices)

    def test_negative_duration_is_invalid(self):
        data = self._valid_data()
        # PositiveIntegerField already rejects negatives at field level,
        # but the clean() double-checks; either way the form must be invalid.
        data["duration_minutes"] = -5
        form = ExerciseEntryForm(data=data)
        self.assertFalse(form.is_valid())

    def test_negative_calories_burned_is_invalid(self):
        data = self._valid_data()
        data["calories_burned"] = "-10.00"
        form = ExerciseEntryForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("calories_burned", form.errors)

    def test_zero_duration_is_valid(self):
        data = self._valid_data()
        data["duration_minutes"] = 0
        form = ExerciseEntryForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_calories_burned_optional(self):
        data = self._valid_data()
        data["calories_burned"] = ""
        form = ExerciseEntryForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_exercise_name_is_invalid(self):
        data = self._valid_data()
        data["exercise_name"] = ""
        form = ExerciseEntryForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("exercise_name", form.errors)


class WorkoutPlanFormTests(TestCase):
    """Tests for WorkoutPlanForm."""

    def _valid_data(self):
        return {
            "name": "Strength Cycle",
            "goal_focus": "Muscle gain",
            "sessions_per_week": 4,
            "details": "Push/pull/legs split",
        }

    def test_valid_data_is_valid(self):
        form = WorkoutPlanForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_sessions_per_week_zero_is_invalid(self):
        data = self._valid_data()
        data["sessions_per_week"] = 0
        form = WorkoutPlanForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("sessions_per_week", form.errors)

    def test_sessions_per_week_one_is_valid(self):
        data = self._valid_data()
        data["sessions_per_week"] = 1
        form = WorkoutPlanForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_name_is_invalid(self):
        data = self._valid_data()
        data["name"] = ""
        form = WorkoutPlanForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_optional_fields_can_be_blank(self):
        data = self._valid_data()
        data["goal_focus"] = ""
        data["details"] = ""
        form = WorkoutPlanForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


# ---------------------------------------------------------------------------
# 4. Helper: _workout_period
# ---------------------------------------------------------------------------

class WorkoutPeriodHelperTests(TestCase):
    """Tests for _workout_period()."""

    def test_day_period(self):
        period, start, end, prev_start, prev_end = _workout_period("day")
        today = timezone.localdate()
        self.assertEqual(period, "day")
        self.assertEqual(start, today)
        self.assertEqual(end, today)
        self.assertEqual(prev_end, today - timedelta(days=1))
        self.assertEqual(prev_start, today - timedelta(days=1))

    def test_week_period(self):
        period, start, end, prev_start, prev_end = _workout_period("week")
        today = timezone.localdate()
        self.assertEqual(period, "week")
        self.assertEqual(start, today - timedelta(days=6))
        self.assertEqual(end, today)
        self.assertEqual(prev_end, start - timedelta(days=1))
        self.assertEqual(prev_start, prev_end - timedelta(days=6))

    def test_month_period(self):
        period, start, end, prev_start, prev_end = _workout_period("month")
        today = timezone.localdate()
        self.assertEqual(period, "month")
        self.assertEqual(start, today - timedelta(days=29))
        self.assertEqual(end, today)
        self.assertEqual(prev_end, start - timedelta(days=1))
        self.assertEqual(prev_start, prev_end - timedelta(days=29))

    def test_invalid_period_defaults_to_week(self):
        period, start, end, prev_start, prev_end = _workout_period("invalid_value")
        today = timezone.localdate()
        self.assertEqual(period, "week")
        self.assertEqual(start, today - timedelta(days=6))

    def test_empty_string_defaults_to_week(self):
        period, *_ = _workout_period("")
        self.assertEqual(period, "week")


# ---------------------------------------------------------------------------
# 5. Views
# ---------------------------------------------------------------------------

class BaseViewTestCase(TestCase):
    """Shared setUp for all view tests."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="TestPass123!")

    def _create_workout(self, name="Test Workout", user=None):
        return Workout.objects.create(
            user=user or self.user,
            name=name,
            performed_on=timezone.localdate(),
        )

    def _create_exercise(self, workout, name="Push-up"):
        return ExerciseEntry.objects.create(
            user=self.user,
            workout=workout,
            exercise_name=name,
            duration_minutes=30,
        )

    def _create_plan(self, name="My Plan"):
        return WorkoutPlan.objects.create(
            user=self.user,
            name=name,
            sessions_per_week=3,
        )

    def _get(self, url, **kwargs):
        return self.client.get(url, **kwargs)

    def _post(self, url, data=None, **kwargs):
        return self.client.post(url, data or {}, **kwargs)

    def assertResponseOK(self, response):
        self.assertEqual(response.status_code, 200)

    def _expect_404(self, url, method="get", data=None):
        if method == "get":
            response = self.client.get(url)
        else:
            response = self.client.post(url, data or {})
        self.assertEqual(response.status_code, 404)


class HomeViewTests(BaseViewTestCase):
    def test_get_returns_200(self):
        response = self._get(reverse("workouts:home"))
        self.assertResponseOK(response)

    def test_context_contains_chart_data_keys(self):
        response = self._get(reverse("workouts:home"))
        self.assertResponseOK(response)
        self.assertIn("calories_chart", response.context)
        self.assertIn("water_chart", response.context)
        self.assertIn("macros_chart", response.context)

    def test_context_contains_workouts(self):
        response = self._get(reverse("workouts:home"))
        self.assertResponseOK(response)
        self.assertIn("workouts", response.context)

    def test_redirects_unauthenticated_user(self):
        self.client.logout()
        response = self.client.get(reverse("workouts:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])


class WorkoutListViewTests(BaseViewTestCase):
    def test_get_returns_200(self):
        response = self._get(reverse("workouts:list"))
        self.assertResponseOK(response)

    def test_default_period_is_week(self):
        response = self._get(reverse("workouts:list"))
        self.assertResponseOK(response)
        self.assertEqual(response.context["period"], "week")

    def test_period_param_month(self):
        response = self._get(reverse("workouts:list") + "?period=month")
        self.assertResponseOK(response)
        self.assertEqual(response.context["period"], "month")

    def test_period_param_day(self):
        response = self._get(reverse("workouts:list") + "?period=day")
        self.assertResponseOK(response)
        self.assertEqual(response.context["period"], "day")

    def test_only_shows_own_workouts(self):
        other = User.objects.create_user(username="other", password="pass")
        Workout.objects.create(user=other, name="Other's Workout", performed_on=timezone.localdate())
        self._create_workout("My Workout")
        response = self._get(reverse("workouts:list"))
        self.assertResponseOK(response)
        for w in response.context["workouts"]:
            self.assertEqual(w.user, self.user)

    def test_redirects_unauthenticated_user(self):
        self.client.logout()
        response = self.client.get(reverse("workouts:list"))
        self.assertEqual(response.status_code, 302)


class WorkoutAddViewTests(BaseViewTestCase):
    def test_get_returns_200(self):
        response = self._get(reverse("workouts:add"))
        self.assertResponseOK(response)

    def test_post_valid_creates_workout_and_redirects(self):
        response = self.client.post(reverse("workouts:add"), {
            "name": "New Workout",
            "performed_on": "2026-04-14",
            "notes": "",
        })
        # workout_add on success redirects (302) — no template rendered at this step.
        self.assertEqual(Workout.objects.filter(user=self.user, name="New Workout").count(), 1)
        workout = Workout.objects.get(user=self.user, name="New Workout")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("workouts:detail", kwargs={"workout_id": workout.id}),
        )

    def test_post_invalid_returns_200_with_errors(self):
        response = self._post(reverse("workouts:add"), {
            "name": "",
            "performed_on": "2026-04-14",
        })
        self.assertResponseOK(response)
        self.assertFalse(response.context["form"].is_valid())


class WorkoutEditViewTests(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.workout = self._create_workout()

    def test_get_returns_200(self):
        response = self._get(reverse("workouts:edit", kwargs={"workout_id": self.workout.id}))
        self.assertResponseOK(response)

    def test_post_valid_updates_workout_and_redirects(self):
        response = self.client.post(
            reverse("workouts:edit", kwargs={"workout_id": self.workout.id}),
            {
                "name": "Updated Workout",
                "performed_on": "2026-04-14",
                "notes": "updated notes",
            },
        )
        self.workout.refresh_from_db()
        self.assertEqual(self.workout.name, "Updated Workout")
        # workout_edit on success redirects (302)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("workouts:detail", kwargs={"workout_id": self.workout.id}),
        )

    def test_other_users_workout_returns_404(self):
        other = User.objects.create_user(username="other2", password="pass")
        other_workout = Workout.objects.create(user=other, name="Other", performed_on=timezone.localdate())
        self._expect_404(reverse("workouts:edit", kwargs={"workout_id": other_workout.id}))


class WorkoutDeleteViewTests(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.workout = self._create_workout()

    def test_post_deletes_workout_and_redirects_to_list(self):
        wid = self.workout.id
        response = self.client.post(reverse("workouts:delete", kwargs={"workout_id": wid}))
        self.assertFalse(Workout.objects.filter(id=wid).exists())
        # workout_delete always redirects to list (no template rendered → no bug)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("workouts:list"))

    def test_get_does_not_delete(self):
        wid = self.workout.id
        # GET on delete view just redirects (no template rendered)
        self.client.get(reverse("workouts:delete", kwargs={"workout_id": wid}))
        self.assertTrue(Workout.objects.filter(id=wid).exists())

    def test_other_users_workout_returns_404(self):
        other = User.objects.create_user(username="other3", password="pass")
        other_workout = Workout.objects.create(user=other, name="Other", performed_on=timezone.localdate())
        self._expect_404(
            reverse("workouts:delete", kwargs={"workout_id": other_workout.id}),
            method="post",
        )


class WorkoutDetailViewTests(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.workout = self._create_workout()

    def test_get_returns_200(self):
        response = self._get(reverse("workouts:detail", kwargs={"workout_id": self.workout.id}))
        self.assertResponseOK(response)

    def test_other_users_workout_returns_404(self):
        other = User.objects.create_user(username="other4", password="pass")
        other_workout = Workout.objects.create(user=other, name="Other", performed_on=timezone.localdate())
        self._expect_404(reverse("workouts:detail", kwargs={"workout_id": other_workout.id}))

    def test_context_contains_workout(self):
        response = self._get(reverse("workouts:detail", kwargs={"workout_id": self.workout.id}))
        self.assertResponseOK(response)
        self.assertEqual(response.context["workout"], self.workout)


class ExerciseEditViewTests(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.workout = self._create_workout()
        self.exercise = self._create_exercise(self.workout)

    def test_get_returns_200(self):
        response = self._get(
            reverse("workouts:exercise_edit", kwargs={
                "workout_id": self.workout.id,
                "exercise_id": self.exercise.id,
            })
        )
        self.assertResponseOK(response)

    def test_post_valid_updates_and_redirects(self):
        response = self.client.post(
            reverse("workouts:exercise_edit", kwargs={
                "workout_id": self.workout.id,
                "exercise_id": self.exercise.id,
            }),
            {
                "exercise_name": "Pull Up",
                "category": "strength",
                "muscle_group": "back",
                "duration_minutes": 20,
                "calories_burned": "",
            },
        )
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.exercise_name, "Pull Up")
        # exercise_edit on success redirects (302)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("workouts:detail", kwargs={"workout_id": self.workout.id}),
        )

    def test_other_users_exercise_returns_404(self):
        other = User.objects.create_user(username="other5", password="pass")
        other_workout = Workout.objects.create(user=other, name="Other", performed_on=timezone.localdate())
        other_exercise = ExerciseEntry.objects.create(
            user=other, workout=other_workout, exercise_name="squat", duration_minutes=10
        )
        self._expect_404(
            reverse("workouts:exercise_edit", kwargs={
                "workout_id": other_workout.id,
                "exercise_id": other_exercise.id,
            })
        )


class ExerciseDeleteViewTests(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.workout = self._create_workout()
        self.exercise = self._create_exercise(self.workout)

    def test_post_deletes_exercise_and_redirects(self):
        eid = self.exercise.id
        response = self.client.post(
            reverse("workouts:exercise_delete", kwargs={
                "workout_id": self.workout.id,
                "exercise_id": eid,
            })
        )
        self.assertFalse(ExerciseEntry.objects.filter(id=eid).exists())
        # exercise_delete redirects to detail (no template rendered directly)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("workouts:detail", kwargs={"workout_id": self.workout.id}),
        )

    def test_get_does_not_delete(self):
        eid = self.exercise.id
        # GET on delete view redirects without deleting (no template rendered)
        self.client.get(
            reverse("workouts:exercise_delete", kwargs={
                "workout_id": self.workout.id,
                "exercise_id": eid,
            })
        )
        self.assertTrue(ExerciseEntry.objects.filter(id=eid).exists())


class ExerciseLibraryViewTests(BaseViewTestCase):
    """
    The exercise_library view uses ExerciseLibrary.objects.all() which is seeded
    by migration 0006. We only create entries with unique names not present in
    that seed to avoid UniqueConstraint errors, and count relative to base.
    """

    def setUp(self):
        super().setUp()
        # Record the baseline count from migration seed data.
        self._base_count = ExerciseLibrary.objects.count()
        # Add three test-specific entries with names unlikely to conflict.
        ExerciseLibrary.objects.get_or_create(
            name="Test Bench Press XYZ",
            defaults={"category": "strength", "muscle_group": "chest", "description": "Classic chest exercise"},
        )
        ExerciseLibrary.objects.get_or_create(
            name="Test Plank XYZ",
            defaults={"category": "core", "muscle_group": "core", "description": "Core stability hold"},
        )
        ExerciseLibrary.objects.get_or_create(
            name="Test Running XYZ",
            defaults={"category": "cardio_xyz", "muscle_group": "legs", "description": "Cardiovascular exercise"},
        )

    def test_get_returns_200(self):
        response = self._get(reverse("workouts:exercise_library"))
        self.assertResponseOK(response)

    def test_returns_all_items_without_query(self):
        response = self._get(reverse("workouts:exercise_library"))
        self.assertResponseOK(response)
        total = response.context["items"].count()
        self.assertGreaterEqual(total, 3)

    def test_search_filters_by_name(self):
        response = self._get(reverse("workouts:exercise_library") + "?q=Test+Bench+Press+XYZ")
        self.assertResponseOK(response)
        items = list(response.context["items"])
        names = [i.name for i in items]
        self.assertIn("Test Bench Press XYZ", names)

    def test_search_filters_by_category(self):
        response = self._get(reverse("workouts:exercise_library") + "?q=cardio_xyz")
        self.assertResponseOK(response)
        items = list(response.context["items"])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Test Running XYZ")

    def test_search_no_results_returns_empty(self):
        response = self._get(reverse("workouts:exercise_library") + "?q=zzznoresultzzzxxx")
        self.assertResponseOK(response)
        self.assertEqual(response.context["items"].count(), 0)

    def test_search_query_returned_in_context(self):
        response = self._get(reverse("workouts:exercise_library") + "?q=Test+Plank+XYZ")
        self.assertResponseOK(response)
        self.assertEqual(response.context["q"], "Test Plank XYZ")

    def test_redirects_unauthenticated_user(self):
        self.client.logout()
        response = self.client.get(reverse("workouts:exercise_library"))
        self.assertEqual(response.status_code, 302)


class PlanListViewTests(BaseViewTestCase):
    def test_get_returns_200(self):
        response = self._get(reverse("workouts:plan_list"))
        self.assertResponseOK(response)

    def test_only_own_plans_shown(self):
        self._create_plan("My Plan")
        other = User.objects.create_user(username="other6", password="pass")
        WorkoutPlan.objects.create(user=other, name="Other Plan", sessions_per_week=2)
        response = self._get(reverse("workouts:plan_list"))
        self.assertResponseOK(response)
        for plan in response.context["plans"]:
            self.assertEqual(plan.user, self.user)

    def test_redirects_unauthenticated_user(self):
        self.client.logout()
        response = self.client.get(reverse("workouts:plan_list"))
        self.assertEqual(response.status_code, 302)


class PlanAddViewTests(BaseViewTestCase):
    def test_get_returns_200(self):
        response = self._get(reverse("workouts:plan_add"))
        self.assertResponseOK(response)

    def test_post_valid_creates_plan_and_redirects_to_list(self):
        response = self.client.post(reverse("workouts:plan_add"), {
            "name": "Power Building",
            "goal_focus": "Strength",
            "sessions_per_week": 5,
            "details": "Day 1: Squat, Day 2: Bench, ...",
        })
        # plan_add on success redirects (302) — no template rendered at this step.
        self.assertEqual(WorkoutPlan.objects.filter(user=self.user, name="Power Building").count(), 1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("workouts:plan_list"))

    def test_post_invalid_sessions_returns_form_errors(self):
        response = self._post(reverse("workouts:plan_add"), {
            "name": "Bad Plan",
            "goal_focus": "",
            "sessions_per_week": 0,
            "details": "",
        })
        self.assertResponseOK(response)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("sessions_per_week", response.context["form"].errors)


class PlanEditViewTests(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.plan = self._create_plan()

    def test_get_returns_200(self):
        response = self._get(reverse("workouts:plan_edit", kwargs={"plan_id": self.plan.id}))
        self.assertResponseOK(response)

    def test_post_valid_updates_plan_and_redirects(self):
        response = self.client.post(
            reverse("workouts:plan_edit", kwargs={"plan_id": self.plan.id}),
            {
                "name": "Updated Plan",
                "goal_focus": "Fat loss",
                "sessions_per_week": 4,
                "details": "Updated details",
            },
        )
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.name, "Updated Plan")
        # plan_edit on success redirects (302)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("workouts:plan_list"))

    def test_other_users_plan_returns_404(self):
        other = User.objects.create_user(username="other7", password="pass")
        other_plan = WorkoutPlan.objects.create(user=other, name="Other Plan", sessions_per_week=2)
        self._expect_404(reverse("workouts:plan_edit", kwargs={"plan_id": other_plan.id}))


class PlanDeleteViewTests(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.plan = self._create_plan()

    def test_post_deletes_plan_and_redirects_to_list(self):
        pid = self.plan.id
        response = self.client.post(reverse("workouts:plan_delete", kwargs={"plan_id": pid}))
        self.assertFalse(WorkoutPlan.objects.filter(id=pid).exists())
        # plan_delete always redirects to list (no template rendered directly)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("workouts:plan_list"))

    def test_get_does_not_delete(self):
        pid = self.plan.id
        # GET on delete view redirects without deleting (no template rendered)
        self.client.get(reverse("workouts:plan_delete", kwargs={"plan_id": pid}))
        self.assertTrue(WorkoutPlan.objects.filter(id=pid).exists())

    def test_other_users_plan_returns_404(self):
        other = User.objects.create_user(username="other8", password="pass")
        other_plan = WorkoutPlan.objects.create(user=other, name="Other Plan", sessions_per_week=2)
        self._expect_404(
            reverse("workouts:plan_delete", kwargs={"plan_id": other_plan.id}),
            method="post",
        )
