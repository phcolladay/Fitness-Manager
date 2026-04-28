from django import forms

from .models import ExerciseEntry, ExerciseLibrary, Workout, WorkoutPlan


class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ["name", "performed_on", "notes"]
        widgets = {"performed_on": forms.DateInput(attrs={"type": "date"})}


class ExerciseEntryForm(forms.ModelForm):
    exercise_name = forms.ChoiceField(choices=[], label="Exercise name")

    class Meta:
        model = ExerciseEntry
        fields = [
            "exercise_name",
            "category",
            "muscle_group",
            "duration_minutes",
            "calories_burned",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exercise_options = list(
            ExerciseLibrary.objects.order_by("category", "muscle_group", "name").values(
                "name",
                "category",
                "muscle_group",
            )
        )
        choices = [("", "Choose an exercise")]
        known_names = {item["name"] for item in self.exercise_options}
        instance_name = getattr(self.instance, "exercise_name", "") if self.instance.pk else ""
        initial_name = self.initial.get("exercise_name") or instance_name
        bound_name = self.data.get(self.add_prefix("exercise_name")) if self.is_bound else ""

        if instance_name and instance_name not in known_names:
            choices.append((instance_name, instance_name))
            known_names.add(instance_name)
        elif not self.is_bound and initial_name and initial_name not in known_names:
            choices.append((initial_name, initial_name))
            known_names.add(initial_name)

        choices.extend((item["name"], item["name"]) for item in self.exercise_options)
        self.fields["exercise_name"].choices = choices

        if self.is_bound and bound_name == instance_name and bound_name not in known_names:
            self.fields["exercise_name"].choices = [(bound_name, bound_name), *choices]

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
