"""
Idempotent demo data seeder for the FitMan demo user.

Usage:
    python manage.py shell < scripts/seed_demo.py

Creates rich, realistic test data for the `demo` user across all apps so that
every page in the redesigned UI has something meaningful to display.

Safe to re-run: existing rows are wiped before fresh data is inserted, so the
demo account always lands in a known good state.
"""

import os
import random
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import django

# Bootstrap Django (allows running as `python scripts/seed_demo.py` too).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fitness_manager.settings")
try:
    django.setup()
except Exception:
    pass

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.goals.models import Goal
from apps.notifications.models import Notification
from apps.nutrition.models import FoodEntry, WaterEntry
from apps.profiles.models import BodyMeasurement, UserProfile
from apps.workouts.models import ExerciseEntry, ExerciseLibrary, Workout, WorkoutPlan

random.seed(20260407)

User = get_user_model()
USERNAME = "demo"
PASSWORD = "demo12345"


def get_or_create_demo():
    user, created = User.objects.get_or_create(
        username=USERNAME,
        defaults={"email": "demo@fitman.local", "first_name": "Demo", "last_name": "User"},
    )
    if created or not user.has_usable_password():
        user.set_password(PASSWORD)
        user.email = user.email or "demo@fitman.local"
        user.first_name = user.first_name or "Demo"
        user.last_name = user.last_name or "User"
        user.save()
    print(f"[user] {USERNAME} ready (id={user.id}, created={created})")
    return user


def seed_profile(user):
    profile, _ = UserProfile.objects.update_or_create(
        user=user,
        defaults={
            "sex": "male",
            "age_years": 28,
            "height_cm": Decimal("178.0"),
            "weight_kg": Decimal("75.4"),
            "activity_level": "moderate",
            "daily_water_goal_ml": 3000,
        },
    )
    print(f"[profile] BMR/TDEE estimate: {profile.estimated_daily_calories()} kcal")
    return profile


def seed_body_metrics(user):
    BodyMeasurement.objects.filter(user=user).delete()
    today = timezone.localdate()
    rows = []
    # 60 days of measurements, every other day, gentle downward trend.
    base_weight = 78.4
    for offset in range(0, 60, 2):
        day = today - timedelta(days=offset)
        weight = base_weight - (offset * 0.05) + random.uniform(-0.4, 0.4)
        rows.append(
            BodyMeasurement(
                user=user,
                measured_on=day,
                weight_kg=Decimal(f"{weight:.2f}"),
                waist_cm=Decimal(f"{82.5 - offset * 0.04:.2f}"),
                chest_cm=Decimal(f"{102.0 + random.uniform(-0.5, 0.5):.2f}"),
                hip_cm=Decimal(f"{96.0 + random.uniform(-0.4, 0.4):.2f}"),
                body_fat_pct=Decimal(f"{18.5 - offset * 0.03:.1f}"),
                notes="Morning measurement" if offset % 6 == 0 else "",
            )
        )
    BodyMeasurement.objects.bulk_create(rows)
    print(f"[body] {len(rows)} body measurements")


def seed_goals(user):
    Goal.objects.filter(user=user).delete()
    today = timezone.localdate()
    goals = [
        dict(name="Daily calorie target", goal_type="calories",
             target_value=Decimal("2400"), unit="kcal", active=True,
             start_date=today - timedelta(days=14)),
        dict(name="Hit protein every day", goal_type="protein",
             target_value=Decimal("160"), unit="g", active=True,
             start_date=today - timedelta(days=21)),
        dict(name="Stay hydrated", goal_type="water",
             target_value=Decimal("3000"), unit="ml", active=True,
             start_date=today - timedelta(days=30)),
        dict(name="Train 5x per week", goal_type="workouts_per_week",
             target_value=Decimal("5"), unit="sessions", active=True,
             start_date=today - timedelta(days=10)),
        dict(name="Weekly training volume", goal_type="workout_minutes",
             target_value=Decimal("300"), unit="min", active=True,
             start_date=today - timedelta(days=10)),
        dict(name="Old cut goal", goal_type="net_calories",
             target_value=Decimal("1900"), unit="kcal", active=False,
             start_date=today - timedelta(days=120),
             end_date=today - timedelta(days=40)),
    ]
    created = 0
    for spec in goals:
        Goal.objects.create(user=user, **spec)
        created += 1
    print(f"[goals] {created} goals")


FOOD_LIBRARY = [
    # (name, brand, qty, unit, kcal, protein, carbs, fat, fiber, sugar, sodium)
    ("Oatmeal with banana", "Quaker", 1, "bowl", 320, 11, 58, 6, 7, 14, 105),
    ("Greek yogurt", "Fage", 1, "cup", 150, 17, 9, 4, 0, 9, 65),
    ("Chicken breast", "", 200, "g", 330, 62, 0, 7, 0, 0, 130),
    ("Brown rice", "", 150, "g", 165, 4, 35, 1, 2, 0, 5),
    ("Mixed salad", "", 1, "bowl", 220, 6, 14, 16, 5, 6, 280),
    ("Protein shake", "Optimum", 1, "scoop", 130, 24, 4, 1, 1, 2, 80),
    ("Whole eggs", "", 3, "egg", 215, 18, 2, 14, 0, 1, 210),
    ("Banana", "", 1, "fruit", 105, 1, 27, 0, 3, 14, 1),
    ("Almonds", "", 30, "g", 175, 6, 6, 15, 4, 1, 0),
    ("Salmon fillet", "", 180, "g", 360, 39, 0, 23, 0, 0, 90),
    ("Sweet potato", "", 200, "g", 180, 4, 41, 0, 6, 13, 70),
    ("Olive oil", "", 1, "tbsp", 120, 0, 0, 14, 0, 0, 0),
    ("Espresso", "Nespresso", 1, "shot", 5, 0, 1, 0, 0, 0, 5),
    ("Apple", "", 1, "fruit", 95, 0, 25, 0, 4, 19, 2),
    ("Steak sirloin", "", 200, "g", 410, 52, 0, 22, 0, 0, 120),
    ("Pasta bolognese", "", 1, "plate", 620, 28, 75, 22, 6, 9, 480),
]


def seed_food_entries(user):
    FoodEntry.objects.filter(user=user).delete()
    now = timezone.now()
    rows = []
    sources = ["manual", "manual", "usda", "usda", "image"]
    for offset in range(0, 30):
        day = now - timedelta(days=offset)
        # 2-4 meals per day
        meals = random.randint(2, 4)
        meal_hours = random.sample([7, 9, 12, 14, 18, 20], meals)
        for hour in sorted(meal_hours):
            food = random.choice(FOOD_LIBRARY)
            consumed_at = day.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
            micros = None
            if random.random() < 0.4:
                micros = {
                    "vitamin_c_mg": round(random.uniform(5, 90), 1),
                    "iron_mg": round(random.uniform(0.5, 8), 1),
                    "calcium_mg": round(random.uniform(20, 300), 1),
                    "potassium_mg": round(random.uniform(100, 800), 1),
                }
            rows.append(
                FoodEntry(
                    user=user,
                    name=food[0],
                    brand=food[1],
                    quantity=Decimal(str(food[2])),
                    unit=food[3],
                    calories=Decimal(str(food[4])),
                    protein_g=Decimal(str(food[5])),
                    carbs_g=Decimal(str(food[6])),
                    fat_g=Decimal(str(food[7])),
                    fiber_g=Decimal(str(food[8])),
                    sugar_g=Decimal(str(food[9])),
                    sodium_mg=Decimal(str(food[10])),
                    micronutrients=micros,
                    source=random.choice(sources),
                    consumed_at=consumed_at,
                )
            )
    FoodEntry.objects.bulk_create(rows)
    print(f"[food] {len(rows)} food entries")


def seed_water_entries(user):
    WaterEntry.objects.filter(user=user).delete()
    now = timezone.now()
    rows = []
    for offset in range(0, 21):
        day = now - timedelta(days=offset)
        # 3-7 glasses per day
        for _ in range(random.randint(3, 7)):
            hour = random.randint(7, 22)
            consumed_at = day.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
            rows.append(
                WaterEntry(
                    user=user,
                    amount_ml=random.choice([200, 250, 300, 350, 500]),
                    consumed_at=consumed_at,
                )
            )
    WaterEntry.objects.bulk_create(rows)
    print(f"[water] {len(rows)} water entries")


WORKOUT_TEMPLATES = [
    ("Push Day", [
        ("Bench Press", "strength", "chest", 25, 180),
        ("Overhead Press", "strength", "shoulders", 15, 110),
        ("Tricep Dips", "strength", "arms", 10, 70),
        ("Push Ups", "strength", "chest", 8, 55),
    ]),
    ("Pull Day", [
        ("Pull Ups", "strength", "back", 12, 90),
        ("Barbell Row", "strength", "back", 18, 130),
        ("Bicep Curls", "strength", "arms", 12, 75),
        ("Face Pulls", "strength", "shoulders", 8, 50),
    ]),
    ("Leg Day", [
        ("Back Squat", "strength", "legs", 25, 220),
        ("Romanian Deadlift", "strength", "legs", 18, 170),
        ("Walking Lunges", "strength", "legs", 12, 110),
        ("Calf Raises", "strength", "legs", 8, 50),
    ]),
    ("Cardio Session", [
        ("Treadmill Run", "cardio", "full_body", 35, 360),
        ("Rowing Machine", "cardio", "full_body", 15, 160),
        ("Jump Rope", "cardio", "full_body", 10, 120),
    ]),
    ("Full Body HIIT", [
        ("Burpees", "hiit", "full_body", 10, 130),
        ("Kettlebell Swings", "hiit", "full_body", 12, 150),
        ("Mountain Climbers", "hiit", "core", 8, 90),
        ("Box Jumps", "hiit", "legs", 10, 110),
    ]),
]


def seed_workouts(user):
    Workout.objects.filter(user=user).delete()  # cascades exercises
    today = timezone.localdate()
    sessions = []
    # 14 workouts spread across the last 30 days
    offsets = sorted(random.sample(range(0, 30), 14))
    for offset in offsets:
        template = random.choice(WORKOUT_TEMPLATES)
        workout = Workout.objects.create(
            user=user,
            name=template[0],
            performed_on=today - timedelta(days=offset),
            notes=random.choice([
                "Felt strong, hit all reps.",
                "Tough session but completed.",
                "Lower energy, scaled volume slightly.",
                "",
                "Personal record on top set!",
            ]),
        )
        for ex in template[1]:
            ExerciseEntry.objects.create(
                user=user,
                workout=workout,
                exercise_name=ex[0],
                category=ex[1],
                muscle_group=ex[2],
                duration_minutes=ex[3] + random.randint(-3, 3),
                calories_burned=Decimal(str(ex[4] + random.randint(-15, 15))),
                auto_classified=random.random() < 0.3,
            )
        sessions.append(workout)
    print(f"[workouts] {len(sessions)} workouts with exercises")


def seed_workout_plans(user):
    WorkoutPlan.objects.filter(user=user).delete()
    plans = [
        dict(
            name="Strength PPL Split",
            goal_focus="Strength",
            sessions_per_week=6,
            details=(
                "Push / Pull / Legs across 6 days.\n"
                "- Push: Bench 5x5, OHP 4x6, Dips 3x10\n"
                "- Pull: Deadlift 5x3, Row 4x6, Pulldowns 3x10\n"
                "- Legs: Squat 5x5, RDL 4x8, Lunges 3x12"
            ),
        ),
        dict(
            name="Fat Loss Conditioning",
            goal_focus="Fat Loss",
            sessions_per_week=4,
            details=(
                "Mix of HIIT and steady-state cardio.\n"
                "- Mon: HIIT intervals (20m)\n"
                "- Wed: Steady run (45m)\n"
                "- Fri: Circuit training\n"
                "- Sun: Long hike or bike"
            ),
        ),
        dict(
            name="Endurance Builder",
            goal_focus="Endurance",
            sessions_per_week=5,
            details=(
                "Progressive aerobic block.\n"
                "- Two easy runs, one tempo, one long run\n"
                "- One cross-training day on the bike or rower"
            ),
        ),
    ]
    for spec in plans:
        WorkoutPlan.objects.create(user=user, **spec)
    print(f"[plans] {len(plans)} workout plans")


def seed_notifications(user):
    Notification.objects.filter(user=user).delete()
    now = timezone.now()
    notes = [
        ("inapp", "sent", "Welcome to FitMan! Your dashboard is ready.", 0),
        ("inapp", "sent", "You hit your protein goal yesterday. Nice work!", 1),
        ("email", "sent", "Weekly summary: 4 workouts, 12,500 kcal logged.", 2),
        ("push", "sent", "Time to log lunch — keep your streak going.", 0),
        ("inapp", "pending", "Don't forget tomorrow's leg day session.", 0),
        ("email", "pending", "New body metric reminder is queued.", 0),
        ("push", "failed", "Notification could not be delivered (device offline).", 5),
        ("inapp", "sent", "Hydration reminder: log a glass of water.", 0),
        ("email", "sent", "Your monthly progress report is available.", 7),
    ]
    rows = []
    for channel, status, msg, days_ago in notes:
        rows.append(
            Notification(
                user=user,
                channel=channel,
                status=status,
                message=msg,
                created_at=now - timedelta(days=days_ago, hours=random.randint(0, 12)),
                sent_at=(now - timedelta(days=days_ago)) if status == "sent" else None,
            )
        )
    Notification.objects.bulk_create(rows)
    print(f"[notifications] {len(rows)} notifications")


def seed_exercise_library():
    library = [
        ("Bench Press", "strength", "chest", "Barbell bench press for chest development."),
        ("Back Squat", "strength", "legs", "Compound lower body lift."),
        ("Deadlift", "strength", "back", "Full body posterior chain lift."),
        ("Pull Up", "strength", "back", "Bodyweight back exercise."),
        ("Overhead Press", "strength", "shoulders", "Standing barbell press."),
        ("Plank", "core", "core", "Isometric core hold."),
        ("Treadmill Run", "cardio", "full_body", "Steady-state cardio on a treadmill."),
        ("Rowing Machine", "cardio", "full_body", "Indoor rower for full-body cardio."),
        ("Burpees", "hiit", "full_body", "Full-body conditioning movement."),
        ("Kettlebell Swing", "hiit", "full_body", "Hip-hinge dominant power move."),
    ]
    created = 0
    for name, cat, mg, desc in library:
        _, was_created = ExerciseLibrary.objects.get_or_create(
            name=name,
            defaults={"category": cat, "muscle_group": mg, "description": desc},
        )
        if was_created:
            created += 1
    print(f"[library] +{created} exercise library entries (total {ExerciseLibrary.objects.count()})")


def main():
    user = get_or_create_demo()
    seed_profile(user)
    seed_goals(user)
    seed_body_metrics(user)
    seed_food_entries(user)
    seed_water_entries(user)
    seed_workouts(user)
    seed_workout_plans(user)
    seed_notifications(user)
    seed_exercise_library()
    print("\nDemo seeding complete. Login with: demo / demo12345")


main()
