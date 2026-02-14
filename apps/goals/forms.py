from django import forms

from .models import Goal


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = [
            "name",
            "goal_type",
            "target_value",
            "unit",
            "start_date",
            "end_date",
            "active",
            "notify_email",
            "notify_push",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
