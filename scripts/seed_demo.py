"""
Seed a persistent demo account with rich showcase data.

Usage:
    python scripts/seed_demo.py

The script is idempotent. It resets the demo user's showcase rows before
creating fresh data so the account returns to a known presentation state.
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

from fitness_manager.showcase_data import DEMO_PASSWORD, DEMO_USERNAME, get_or_create_demo_user, seed_showcase_data


def main() -> None:
    user = get_or_create_demo_user()
    summary = seed_showcase_data(user)
    print(f"[user] {DEMO_USERNAME} ready (id={user.id})")
    print("[profile] profile ready")
    print(f"[goals] {summary.goals} goals")
    print(f"[body] {summary.body_measurements} body measurements")
    print(f"[food] {summary.food_entries} food entries")
    print(f"[water] {summary.water_entries} water entries")
    print(f"[workouts] {summary.workouts} workouts with {summary.exercise_entries} exercises")
    print(f"[plans] {summary.workout_plans} workout plans")
    print(f"[notifications] {summary.notifications} notifications")
    print(f"[library] +{summary.exercise_library_created} exercise library entries")
    print(f"\nDemo seeding complete. Login with: {DEMO_USERNAME} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
