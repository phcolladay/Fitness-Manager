from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.goals.models import Goal
from apps.notifications.models import Notification
from apps.nutrition.models import FoodEntry, WaterEntry
from apps.profiles.models import BodyMeasurement, UserProfile
from apps.workouts.models import ExerciseEntry, ExerciseLibrary, Workout, WorkoutPlan


SHOWCASE_RANDOM_SEED = 20260407
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo12345"


@dataclass(frozen=True)
class ShowcaseSeedSummary:
    body_measurements: int
    food_entries: int
    water_entries: int
    workouts: int
    exercise_entries: int
    workout_plans: int
    goals: int
    notifications: int
    exercise_library_created: int


FOOD_LIBRARY = [
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


WORKOUT_TEMPLATES = [
    (
        "Push Day",
        [
            ("Bench Press", "strength", "chest", 25, 180),
            ("Overhead Press", "strength", "shoulders", 15, 110),
            ("Tricep Dips", "strength", "arms", 10, 70),
            ("Push Ups", "strength", "chest", 8, 55),
        ],
    ),
    (
        "Pull Day",
        [
            ("Pull Ups", "strength", "back", 12, 90),
            ("Barbell Row", "strength", "back", 18, 130),
            ("Bicep Curls", "strength", "arms", 12, 75),
            ("Face Pulls", "strength", "shoulders", 8, 50),
        ],
    ),
    (
        "Leg Day",
        [
            ("Back Squat", "strength", "legs", 25, 220),
            ("Romanian Deadlift", "strength", "legs", 18, 170),
            ("Walking Lunges", "strength", "legs", 12, 110),
            ("Calf Raises", "strength", "legs", 8, 50),
        ],
    ),
    (
        "Cardio Session",
        [
            ("Treadmill Run", "cardio", "full_body", 35, 360),
            ("Rowing Machine", "cardio", "full_body", 15, 160),
            ("Jump Rope", "cardio", "full_body", 10, 120),
        ],
    ),
    (
        "Full Body HIIT",
        [
            ("Burpees", "hiit", "full_body", 10, 130),
            ("Kettlebell Swings", "hiit", "full_body", 12, 150),
            ("Mountain Climbers", "hiit", "core", 8, 90),
            ("Box Jumps", "hiit", "legs", 10, 110),
        ],
    ),
]


EXERCISE_LIBRARY = [
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


def get_or_create_demo_user():
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=DEMO_USERNAME,
        defaults={"email": "demo@fitman.local", "first_name": "Demo", "last_name": "User"},
    )
    if created or not user.has_usable_password():
        user.set_password(DEMO_PASSWORD)
        user.email = user.email or "demo@fitman.local"
        user.first_name = user.first_name or "Demo"
        user.last_name = user.last_name or "User"
        user.save(update_fields=["password", "email", "first_name", "last_name"])
    return user


@transaction.atomic
def seed_showcase_data(user, *, reset: bool = True) -> ShowcaseSeedSummary:
    rng = random.Random(SHOWCASE_RANDOM_SEED)
    if reset:
        _clear_user_showcase_data(user)

    _seed_profile(user)
    goals_count = _seed_goals(user)
    body_count = _seed_body_metrics(user, rng)
    food_count = _seed_food_entries(user, rng)
    water_count = _seed_water_entries(user, rng)
    workout_count, exercise_count = _seed_workouts(user, rng)
    plan_count = _seed_workout_plans(user)
    notification_count = _seed_notifications(user, rng)
    library_created = _seed_exercise_library()

    return ShowcaseSeedSummary(
        body_measurements=body_count,
        food_entries=food_count,
        water_entries=water_count,
        workouts=workout_count,
        exercise_entries=exercise_count,
        workout_plans=plan_count,
        goals=goals_count,
        notifications=notification_count,
        exercise_library_created=library_created,
    )


def _clear_user_showcase_data(user) -> None:
    Notification.objects.filter(user=user).delete()
    WorkoutPlan.objects.filter(user=user).delete()
    Workout.objects.filter(user=user).delete()
    FoodEntry.objects.filter(user=user).delete()
    WaterEntry.objects.filter(user=user).delete()
    BodyMeasurement.objects.filter(user=user).delete()
    Goal.objects.filter(user=user).delete()


def _seed_profile(user) -> None:
    UserProfile.objects.update_or_create(
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


def _seed_goals(user) -> int:
    today = timezone.localdate()
    goals = [
        {
            "name": "Daily calorie target",
            "goal_type": "calories",
            "target_value": Decimal("2400"),
            "unit": "kcal",
            "active": True,
            "start_date": today - timedelta(days=14),
        },
        {
            "name": "Hit protein every day",
            "goal_type": "protein",
            "target_value": Decimal("160"),
            "unit": "g",
            "active": True,
            "start_date": today - timedelta(days=21),
        },
        {
            "name": "Stay hydrated",
            "goal_type": "water",
            "target_value": Decimal("3000"),
            "unit": "ml",
            "active": True,
            "start_date": today - timedelta(days=30),
        },
        {
            "name": "Train 5x per week",
            "goal_type": "workouts_per_week",
            "target_value": Decimal("5"),
            "unit": "sessions",
            "active": True,
            "start_date": today - timedelta(days=10),
        },
        {
            "name": "Weekly training volume",
            "goal_type": "workout_minutes",
            "target_value": Decimal("300"),
            "unit": "min",
            "active": True,
            "start_date": today - timedelta(days=10),
        },
        {
            "name": "Old cut goal",
            "goal_type": "net_calories",
            "target_value": Decimal("1900"),
            "unit": "kcal",
            "active": False,
            "start_date": today - timedelta(days=120),
            "end_date": today - timedelta(days=40),
        },
    ]
    Goal.objects.bulk_create([Goal(user=user, **goal) for goal in goals])
    return len(goals)


def _seed_body_metrics(user, rng: random.Random) -> int:
    today = timezone.localdate()
    rows = []
    base_weight = 78.4
    for offset in range(0, 60, 2):
        weight = base_weight - (offset * 0.05) + rng.uniform(-0.4, 0.4)
        rows.append(
            BodyMeasurement(
                user=user,
                measured_on=today - timedelta(days=offset),
                weight_kg=Decimal(f"{weight:.2f}"),
                waist_cm=Decimal(f"{82.5 - offset * 0.04:.2f}"),
                chest_cm=Decimal(f"{102.0 + rng.uniform(-0.5, 0.5):.2f}"),
                hip_cm=Decimal(f"{96.0 + rng.uniform(-0.4, 0.4):.2f}"),
                body_fat_pct=Decimal(f"{18.5 - offset * 0.03:.1f}"),
                notes="Morning measurement" if offset % 6 == 0 else "",
            )
        )
    BodyMeasurement.objects.bulk_create(rows)
    return len(rows)


def _seed_food_entries(user, rng: random.Random) -> int:
    now = timezone.now()
    rows = []
    sources = ["manual", "manual", "usda", "usda", "image"]
    for offset in range(0, 30):
        day = now - timedelta(days=offset)
        meal_hours = rng.sample([7, 9, 12, 14, 18, 20], rng.randint(2, 4))
        for hour in sorted(meal_hours):
            food = rng.choice(FOOD_LIBRARY)
            consumed_at = day.replace(hour=hour, minute=rng.randint(0, 59), second=0, microsecond=0)
            micros = None
            if rng.random() < 0.4:
                micros = {
                    "vitamin_c_mg": round(rng.uniform(5, 90), 1),
                    "iron_mg": round(rng.uniform(0.5, 8), 1),
                    "calcium_mg": round(rng.uniform(20, 300), 1),
                    "potassium_mg": round(rng.uniform(100, 800), 1),
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
                    source=rng.choice(sources),
                    consumed_at=consumed_at,
                )
            )
    FoodEntry.objects.bulk_create(rows)
    return len(rows)


def _seed_water_entries(user, rng: random.Random) -> int:
    now = timezone.now()
    rows = []
    for offset in range(0, 21):
        day = now - timedelta(days=offset)
        for _ in range(rng.randint(3, 7)):
            consumed_at = day.replace(
                hour=rng.randint(7, 22),
                minute=rng.randint(0, 59),
                second=0,
                microsecond=0,
            )
            rows.append(
                WaterEntry(
                    user=user,
                    amount_ml=rng.choice([200, 250, 300, 350, 500]),
                    consumed_at=consumed_at,
                )
            )
    WaterEntry.objects.bulk_create(rows)
    return len(rows)


def _seed_workouts(user, rng: random.Random) -> tuple[int, int]:
    today = timezone.localdate()
    workouts = 0
    exercises = 0
    offsets = sorted(rng.sample(range(0, 30), 14))
    for offset in offsets:
        name, exercise_specs = rng.choice(WORKOUT_TEMPLATES)
        workout = Workout.objects.create(
            user=user,
            name=name,
            performed_on=today - timedelta(days=offset),
            notes=rng.choice(
                [
                    "Felt strong, hit all reps.",
                    "Tough session but completed.",
                    "Lower energy, scaled volume slightly.",
                    "",
                    "Personal record on top set!",
                ]
            ),
        )
        workouts += 1
        for exercise in exercise_specs:
            ExerciseEntry.objects.create(
                user=user,
                workout=workout,
                exercise_name=exercise[0],
                category=exercise[1],
                muscle_group=exercise[2],
                duration_minutes=max(1, exercise[3] + rng.randint(-3, 3)),
                calories_burned=Decimal(str(max(0, exercise[4] + rng.randint(-15, 15)))),
                auto_classified=rng.random() < 0.3,
            )
            exercises += 1
    return workouts, exercises


def _seed_workout_plans(user) -> int:
    plans = [
        {
            "name": "Strength PPL Split",
            "goal_focus": "Strength",
            "sessions_per_week": 6,
            "details": (
                "Push / Pull / Legs across 6 days.\n"
                "- Push: Bench 5x5, OHP 4x6, Dips 3x10\n"
                "- Pull: Deadlift 5x3, Row 4x6, Pulldowns 3x10\n"
                "- Legs: Squat 5x5, RDL 4x8, Lunges 3x12"
            ),
        },
        {
            "name": "Fat Loss Conditioning",
            "goal_focus": "Fat Loss",
            "sessions_per_week": 4,
            "details": (
                "Mix of HIIT and steady-state cardio.\n"
                "- Mon: HIIT intervals (20m)\n"
                "- Wed: Steady run (45m)\n"
                "- Fri: Circuit training\n"
                "- Sun: Long hike or bike"
            ),
        },
        {
            "name": "Endurance Builder",
            "goal_focus": "Endurance",
            "sessions_per_week": 5,
            "details": (
                "Progressive aerobic block.\n"
                "- Two easy runs, one tempo, one long run\n"
                "- One cross-training day on the bike or rower"
            ),
        },
    ]
    WorkoutPlan.objects.bulk_create([WorkoutPlan(user=user, **plan) for plan in plans])
    return len(plans)


def _seed_notifications(user, rng: random.Random) -> int:
    now = timezone.now()
    notes = [
        ("inapp", "sent", "Welcome to TerrierFit! Your dashboard is ready.", 0),
        ("inapp", "sent", "You hit your protein goal yesterday.", 1),
        ("email", "sent", "Weekly summary: 4 workouts, 12,500 kcal logged.", 2),
        ("push", "sent", "Time to log lunch and keep your streak going.", 0),
        ("inapp", "pending", "Tomorrow's leg day session is queued.", 0),
        ("email", "pending", "New body metric reminder is queued.", 0),
        ("push", "failed", "Notification could not be delivered because the device is offline.", 5),
        ("inapp", "sent", "Hydration reminder: log a glass of water.", 0),
        ("email", "sent", "Your monthly progress report is available.", 7),
    ]
    rows = []
    for channel, status, message, days_ago in notes:
        sent_at = now - timedelta(days=days_ago) if status == "sent" else None
        rows.append(
            Notification(
                user=user,
                channel=channel,
                status=status,
                message=message,
                created_at=now - timedelta(days=days_ago, hours=rng.randint(0, 12)),
                sent_at=sent_at,
            )
        )
    Notification.objects.bulk_create(rows)
    return len(rows)


def _seed_exercise_library() -> int:
    created = 0
    for name, category, muscle_group, description in EXERCISE_LIBRARY:
        _, was_created = ExerciseLibrary.objects.get_or_create(
            name=name,
            defaults={
                "category": category,
                "muscle_group": muscle_group,
                "description": description,
            },
        )
        if was_created:
            created += 1
    return created
