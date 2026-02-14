from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def _get_or_create_legacy_user(apps):
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)

    existing = User.objects.order_by("id").first()
    if existing:
        return existing

    username_field = getattr(User, "USERNAME_FIELD", "username")
    value = "legacy"
    if username_field == "email":
        value = "legacy@local"
    kwargs = {username_field: value}
    if "email" in [f.name for f in User._meta.fields]:
        kwargs.setdefault("email", "legacy@local")
    if "is_active" in [f.name for f in User._meta.fields]:
        kwargs.setdefault("is_active", False)

    user = User.objects.create(**kwargs)
    if hasattr(user, "set_unusable_password"):
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def backfill_workout_users(apps, schema_editor):
    Workout = apps.get_model("workouts", "Workout")
    ExerciseEntry = apps.get_model("workouts", "ExerciseEntry")

    legacy_user = _get_or_create_legacy_user(apps)

    # If an exercise has no user but the parent workout does, inherit it.
    for entry in ExerciseEntry.objects.filter(user__isnull=True).select_related("workout"):
        workout_user_id = getattr(entry.workout, "user_id", None)
        entry.user_id = workout_user_id or legacy_user.id
        entry.save(update_fields=["user"])
    Workout.objects.filter(user__isnull=True).update(user=legacy_user)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("workouts", "0003_exerciseentry_user_workout_user"),
    ]

    operations = [
        migrations.RunPython(backfill_workout_users, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="workout",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="workouts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="exerciseentry",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="exercise_entries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
