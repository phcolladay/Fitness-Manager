from django import forms

from .models import ExerciseEntry, Workout


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
