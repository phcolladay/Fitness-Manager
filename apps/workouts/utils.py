EXERCISE_CATEGORIES = {
    "run": ("cardio", "legs"),
    "jog": ("cardio", "legs"),
    "cycle": ("cardio", "legs"),
    "bike": ("cardio", "legs"),
    "swim": ("cardio", "full body"),
    "bench": ("strength", "chest"),
    "push": ("strength", "chest"),
    "pull": ("strength", "back"),
    "row": ("strength", "back"),
    "squat": ("strength", "legs"),
    "deadlift": ("strength", "back"),
    "plank": ("core", "core"),
    "yoga": ("mobility", "full body"),
}


CALORIES_PER_MINUTE = {
    "cardio": 8.0,
    "hiit": 10.0,
    "strength": 6.0,
    "core": 5.0,
    "mobility": 3.0,
}


def classify_exercise(name: str) -> tuple[str, str]:
    lowered = name.lower()
    for keyword, (category, muscle) in EXERCISE_CATEGORIES.items():
        if keyword in lowered:
            return category, muscle
    return "general", ""


def estimate_calories(category: str, duration_minutes: int) -> float:
    per_minute = CALORIES_PER_MINUTE.get(category, 5.0)
    return round(per_minute * max(duration_minutes, 0), 2)
