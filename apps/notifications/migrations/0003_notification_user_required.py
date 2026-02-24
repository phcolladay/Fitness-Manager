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


def backfill_notification_users(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    legacy_user = _get_or_create_legacy_user(apps)

    for n in Notification.objects.filter(user__isnull=True).select_related("goal"):
        goal_user_id = getattr(n.goal, "user_id", None) if n.goal_id else None
        n.user_id = goal_user_id or legacy_user.id
        n.save(update_fields=["user"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("goals", "0003_goal_user_required"),
        ("notifications", "0002_notification_user"),
    ]

    operations = [
        migrations.RunPython(backfill_notification_users, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="notification",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
