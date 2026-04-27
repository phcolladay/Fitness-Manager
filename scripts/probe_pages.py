"""
Probe every redesigned page as the demo user using Django's test client.

Reports HTTP status, response size, and a couple of sanity checks (looks for
expected text from the seeded data) so we can quickly tell whether a page is
rendering or blowing up.
"""

import os
import sys
from pathlib import Path

import django

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fitness_manager.settings")
django.setup()

from django.test import Client
from django.urls import reverse

from apps.goals.models import Goal
from apps.nutrition.models import FoodEntry, WaterEntry
from apps.profiles.models import BodyMeasurement
from apps.workouts.models import Workout, WorkoutPlan


def first_id(model, user):
    obj = model.objects.filter(user=user).order_by("id").first()
    return obj.id if obj else None


def main():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.get(username="demo")

    client = Client()
    assert client.login(username="demo", password="demo12345"), "demo login failed"

    workout_id = first_id(Workout, user)
    plan_id = first_id(WorkoutPlan, user)
    goal_id = first_id(Goal, user)
    food_id = first_id(FoodEntry, user)
    water_id = first_id(WaterEntry, user)
    body_id = first_id(BodyMeasurement, user)

    # (label, url, optional needle to assert appears in HTML)
    probes = [
        ("home", reverse("workouts:home"), None),
        ("workouts:list", reverse("workouts:list"), None),
        ("workouts:add", reverse("workouts:add"), None),
        ("workouts:detail", reverse("workouts:detail", args=[workout_id]), None),
        ("workouts:edit", reverse("workouts:edit", args=[workout_id]), None),
        ("workouts:exercise_add", reverse("workouts:exercise_add", args=[workout_id]), None),
        ("workouts:exercise_library", reverse("workouts:exercise_library"), "Bench Press"),
        ("workouts:plan_list", reverse("workouts:plan_list"), "Strength PPL Split"),
        ("workouts:plan_add", reverse("workouts:plan_add"), None),
        ("workouts:plan_edit", reverse("workouts:plan_edit", args=[plan_id]), None),
        ("nutrition:list", reverse("nutrition:list"), None),
        ("nutrition:add", reverse("nutrition:add"), None),
        ("nutrition:edit", reverse("nutrition:edit", args=[food_id]), None),
        ("nutrition:summary", reverse("nutrition:summary"), None),
        ("nutrition:lookup", reverse("nutrition:lookup"), None),
        ("nutrition:estimate", reverse("nutrition:estimate"), None),
        ("nutrition:photo_upload", reverse("nutrition:photo_upload"), None),
        ("nutrition:water_list", reverse("nutrition:water_list"), None),
        ("nutrition:water_add", reverse("nutrition:water_add"), None),
        ("nutrition:water_edit", reverse("nutrition:water_edit", args=[water_id]), None),
        ("goals:list", reverse("goals:list"), "Daily calorie target"),
        ("goals:add", reverse("goals:add"), None),
        ("goals:edit", reverse("goals:edit", args=[goal_id]), None),
        ("notifications:list", reverse("notifications:list"), "Welcome to FitMan"),
        ("profiles:profile", reverse("profiles:profile"), None),
        ("profiles:body_metrics", reverse("profiles:body_metrics"), None),
        ("profiles:body_metrics_add", reverse("profiles:body_metrics_add"), None),
        ("profiles:body_metrics_edit", reverse("profiles:body_metrics_edit", args=[body_id]), None),
    ]

    fails = 0
    for label, url, needle in probes:
        try:
            resp = client.get(url, follow=True)
        except Exception as exc:
            print(f"FAIL  {label:35s} {url}  -> EXCEPTION: {exc}")
            fails += 1
            continue
        size = len(resp.content)
        status = resp.status_code
        body = resp.content.decode("utf-8", errors="replace")
        needle_ok = (needle is None) or (needle in body)
        ok = status == 200 and needle_ok
        marker = " OK " if ok else "FAIL"
        if not ok:
            fails += 1
        suffix = ""
        if needle and not needle_ok:
            suffix = f"  (missing needle: {needle!r})"
        print(f"{marker}  {label:35s} {url:55s} {status}  {size:>7d}b{suffix}")

    # Anonymous probes
    anon = Client()
    anon_probes = [
        ("login", "/login/"),
        ("signup", "/signup/"),
        ("password_reset", "/password-reset/"),
        ("password_reset_done", "/password-reset/done/"),
        ("password_reset_complete", "/reset/done/"),
    ]
    print("\n-- anonymous --")
    for label, url in anon_probes:
        resp = anon.get(url)
        marker = " OK " if resp.status_code == 200 else "FAIL"
        if resp.status_code != 200:
            fails += 1
        print(f"{marker}  {label:35s} {url:55s} {resp.status_code}  {len(resp.content):>7d}b")

    print(f"\n{'OK' if fails == 0 else 'FAILURES: ' + str(fails)}  total checks: {len(probes) + len(anon_probes)}")
    sys.exit(0 if fails == 0 else 1)


main()
