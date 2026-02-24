from django import forms

from .models import ExerciseEntry, Workout, WorkoutPlan


class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ["name", "performed_on", "notes"]
        widgets = {"performed_on": forms.DateInput(attrs={"type": "date"})}


class ExerciseEntryForm(forms.ModelForm):
    class Meta:
        model = ExerciseEntry
        fields = [
            "exercise_name",
            "category",
            "muscle_group",
            "duration_minutes",
            "calories_burned",
        ]

    def clean(self):
        cleaned = super().clean()
        for field in ["duration_minutes", "calories_burned"]:
            value = cleaned.get(field)
            if value is not None and value < 0:
                self.add_error(field, "Value must be non-negative.")
        return cleaned


class WorkoutPlanForm(forms.ModelForm):
    class Meta:
        model = WorkoutPlan
        fields = ["name", "goal_focus", "sessions_per_week", "details"]

    def clean_sessions_per_week(self):
        value = self.cleaned_data["sessions_per_week"]
        if value < 1:
            raise forms.ValidationError("Sessions per week must be at least 1.")
        return value
