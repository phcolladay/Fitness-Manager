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


def backfill_nutrition_users(apps, schema_editor):
    FoodEntry = apps.get_model("nutrition", "FoodEntry")
    WaterEntry = apps.get_model("nutrition", "WaterEntry")
    FoodPhoto = apps.get_model("nutrition", "FoodPhoto")

    legacy_user = _get_or_create_legacy_user(apps)
    FoodEntry.objects.filter(user__isnull=True).update(user=legacy_user)
    WaterEntry.objects.filter(user__isnull=True).update(user=legacy_user)
    FoodPhoto.objects.filter(user__isnull=True).update(user=legacy_user)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("nutrition", "0002_foodentry_user_foodphoto_user_waterentry_user_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_nutrition_users, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="foodentry",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="food_entries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="waterentry",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="water_entries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="foodphoto",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="food_photos",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

