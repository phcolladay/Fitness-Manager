from django.contrib import admin

from .models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("name", "goal_type", "target_value", "unit", "active", "user")
    list_filter = ("goal_type", "active", "user")

# Register your models here.
