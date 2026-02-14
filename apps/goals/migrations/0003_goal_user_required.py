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


def backfill_goal_user(apps, schema_editor):
    Goal = apps.get_model("goals", "Goal")
    legacy_user = _get_or_create_legacy_user(apps)
    Goal.objects.filter(user__isnull=True).update(user=legacy_user)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("goals", "0002_goal_user"),
    ]

    operations = [
        migrations.RunPython(backfill_goal_user, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="goal",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="goals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

