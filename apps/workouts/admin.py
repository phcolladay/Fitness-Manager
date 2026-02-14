from django.contrib import admin

from .models import ExerciseEntry, Workout


class ExerciseEntryInline(admin.TabularInline):
    model = ExerciseEntry
    extra = 0


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ("name", "performed_on", "user")
    search_fields = ("name",)
    inlines = [ExerciseEntryInline]


@admin.register(ExerciseEntry)
class ExerciseEntryAdmin(admin.ModelAdmin):
    list_display = (
        "exercise_name",
        "workout",
        "user",
        "category",
        "muscle_group",
        "duration_minutes",
        "calories_burned",
    )
    list_filter = ("workout", "category", "muscle_group", "user")

# Register your models here.
