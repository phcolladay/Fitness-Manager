import os
import re
import unittest

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from apps.goals.models import Goal
from apps.nutrition.models import FoodEntry, WaterEntry
from apps.profiles.models import BodyMeasurement
from apps.workouts.models import ExerciseEntry, Workout

# Playwright's sync API runs an event loop internally. Django's async-safety
# guard can otherwise reject normal ORM calls in this synchronous test case.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - dev dependency may be absent locally.
    PlaywrightError = Exception
    sync_playwright = None


@unittest.skipUnless(sync_playwright, "Playwright Python package is not installed.")
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CSRF_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
)
class PlaywrightUserFlowsTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        launch_options = {"headless": True}
        executable_path = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        if executable_path:
            launch_options["executable_path"] = executable_path
        try:
            cls.browser = cls.playwright.chromium.launch(**launch_options)
        except PlaywrightError as exc:  # pragma: no cover - only hit on missing local browser.
            cls.playwright.stop()
            raise unittest.SkipTest(f"Chromium is not installed for Playwright: {exc}") from exc

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 390, "height": 844})
        self.page = self.context.new_page()
        self.User = get_user_model()
        mail.outbox = []

    def tearDown(self):
        self.context.close()

    def _new_page(self, viewport=None):
        self.context.close()
        self.context = self.browser.new_context(viewport=viewport or {"width": 390, "height": 844})
        self.page = self.context.new_page()

    def _signup_user(self, email, password="demo12345", username=None):
        self.page.goto(f"{self.live_server_url}{reverse('signup')}")
        self.page.fill('input[name="email"]', email)
        if username:
            self.page.fill('input[name="username"]', username)
        self.page.fill('input[name="password1"]', password)
        self.page.fill('input[name="password2"]', password)
        self._submit()
        self.assertEqual(self.page.url.rstrip("/"), self.live_server_url.rstrip("/"))
        return self.User.objects.get(email=email)

    def _login(self, username="demo", password="demo12345"):
        self.page.goto(f"{self.live_server_url}{reverse('login')}")
        self.page.fill('input[name="username"]', username)
        self.page.fill('input[name="password"]', password)
        with self.page.expect_navigation():
            self.page.click('button[type="submit"]')
        self.assertEqual(self.page.url.rstrip("/"), self.live_server_url.rstrip("/"))

    def _submit(self):
        invalid_fields = self.page.locator("form.fm-form :invalid").evaluate_all(
            "(els) => els.map((el) => ({name: el.name, id: el.id, message: el.validationMessage}))"
        )
        self.assertEqual([], invalid_fields)
        with self.page.expect_navigation():
            self.page.click('form.fm-form button[type="submit"]:not([name])')

    def test_login_and_mobile_layout_pages_do_not_overflow(self):
        self._signup_user("demo@example.com", username="demo")
        self._new_page()
        self._login()

        paths = [
            reverse("workouts:home"),
            reverse("nutrition:list"),
            reverse("nutrition:water_list"),
            reverse("workouts:list"),
            reverse("profiles:body_metrics"),
            reverse("profiles:profile"),
            reverse("goals:list"),
            reverse("notifications:list"),
        ]

        for width in (390, 320):
            self.page.set_viewport_size({"width": width, "height": 844})
            for path in paths:
                self.page.goto(f"{self.live_server_url}{path}")
                metrics = self.page.evaluate(
                    """
                    () => {
                      const active = document.querySelector('.fm-sidebar-link.is-active');
                      const rect = active ? active.getBoundingClientRect() : null;
                      return {
                        innerWidth: window.innerWidth,
                        scrollWidth: document.documentElement.scrollWidth,
                        activeHeight: rect ? Math.round(rect.height) : null
                      };
                    }
                    """
                )
                self.assertLessEqual(metrics["scrollWidth"], metrics["innerWidth"] + 1, path)
                if metrics["activeHeight"] is not None:
                    self.assertLessEqual(metrics["activeHeight"], 60, path)

    def test_signup_with_email_only_logs_user_in(self):
        email = "new-e2e@example.com"
        self._signup_user(email, password="StrongPass123!")
        user = self.User.objects.get(email=email)
        self.assertEqual(user.username, "new-e2e")

    def test_password_reset_email_link_changes_password(self):
        self._signup_user("reset@example.com", username="resetuser", password="OldPass123!")
        self._new_page()

        self.page.goto(f"{self.live_server_url}{reverse('password_reset')}")
        self.page.fill('input[name="email"]', "reset@example.com")
        self._submit()
        self.assertIn(reverse("password_reset_done"), self.page.url)
        self.assertEqual(len(mail.outbox), 1)

        match = re.search(r"https?://[^\s]+/reset/[^\s]+", mail.outbox[0].body)
        self.assertIsNotNone(match)
        self.page.goto(match.group(0))
        self.page.fill('input[name="new_password1"]', "NewStrongPass123!")
        self.page.fill('input[name="new_password2"]', "NewStrongPass123!")
        self._submit()
        self.assertIn(reverse("password_reset_complete"), self.page.url)

        self.page.goto(f"{self.live_server_url}{reverse('login')}")
        self.page.fill('input[name="username"]', "reset@example.com")
        self.page.fill('input[name="password"]', "NewStrongPass123!")
        self._submit()
        self.assertEqual(self.page.url.rstrip("/"), self.live_server_url.rstrip("/"))

    def test_core_crud_flows_create_user_scoped_records(self):
        user = self._signup_user("crud@example.com", username="cruduser")
        self._new_page()
        self._login("cruduser")

        self.page.goto(f"{self.live_server_url}{reverse('nutrition:add')}")
        self.page.fill('input[name="name"]', "E2E Greek Yogurt")
        self.page.fill('input[name="brand"]', "E2E Dairy")
        self.page.fill('input[name="quantity"]', "1.25")
        self.page.fill('input[name="unit"]', "serving")
        self.page.fill('input[name="calories"]', "250")
        self.page.fill('input[name="protein_g"]', "24")
        self.page.fill('input[name="carbs_g"]', "22")
        self.page.fill('input[name="fat_g"]', "6")
        self.page.fill('input[name="fiber_g"]', "2")
        self.page.fill('input[name="sugar_g"]', "10")
        self.page.fill('input[name="sodium_mg"]', "90")
        self.page.fill('textarea[name="micronutrients"]', "{}")
        self._submit()
        self.assertIn(reverse("nutrition:list"), self.page.url)
        self.assertTrue(FoodEntry.objects.filter(user=user, name="E2E Greek Yogurt").exists())

        self.page.goto(f"{self.live_server_url}{reverse('nutrition:water_add')}")
        self.page.select_option('select[name="unit"]', "ml")
        self.page.fill('input[name="amount"]', "750")
        self._submit()
        self.assertTrue(WaterEntry.objects.filter(user=user, amount_ml=750).exists())

        self.page.goto(f"{self.live_server_url}{reverse('workouts:add')}")
        self.page.fill('input[name="name"]', "E2E Strength Session")
        self.page.fill('input[name="performed_on"]', timezone.localdate().isoformat())
        self.page.fill('textarea[name="notes"]', "Created by Playwright regression test.")
        self._submit()
        workout = Workout.objects.get(user=user, name="E2E Strength Session")

        self.page.goto(f"{self.live_server_url}{reverse('workouts:exercise_add', args=[workout.id])}")
        self.page.fill('input[name="exercise_name"]', "E2E Bench Press")
        self.page.fill('input[name="category"]', "strength")
        self.page.fill('input[name="muscle_group"]', "chest")
        self.page.fill('input[name="duration_minutes"]', "35")
        self.page.fill('input[name="calories_burned"]', "180")
        self._submit()
        self.assertTrue(ExerciseEntry.objects.filter(user=user, workout=workout, exercise_name="E2E Bench Press").exists())

        self.page.goto(f"{self.live_server_url}{reverse('goals:add')}")
        self.page.fill('input[name="name"]', "E2E Protein Goal")
        self.page.select_option('select[name="goal_type"]', "protein")
        self.page.fill('input[name="target_value"]', "165")
        self.page.fill('input[name="unit"]', "g")
        self.page.fill('input[name="start_date"]', timezone.localdate().isoformat())
        self._submit()
        self.assertTrue(Goal.objects.filter(user=user, name="E2E Protein Goal").exists())

        self.page.goto(f"{self.live_server_url}{reverse('profiles:body_metrics_add')}")
        self.page.fill('input[name="measured_on"]', timezone.localdate().isoformat())
        self.page.fill('input[name="weight_kg"]', "76.2")
        self.page.fill('input[name="waist_cm"]', "82.5")
        self._submit()
        self.assertTrue(BodyMeasurement.objects.filter(user=user, weight_kg="76.2").exists())
