from django import forms

from .models import BodyMeasurement, UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "sex",
            "age_years",
            "height_cm",
            "weight_kg",
            "activity_level",
            "daily_water_goal_ml",
        ]

    def clean(self):
        cleaned = super().clean()
        for field in ["age_years", "height_cm", "weight_kg", "daily_water_goal_ml"]:
            value = cleaned.get(field)
            if value is not None and value < 0:
                self.add_error(field, "Value must be non-negative.")
        return cleaned


class BodyMeasurementForm(forms.ModelForm):
    class Meta:
        model = BodyMeasurement
        fields = [
            "measured_on",
            "weight_kg",
            "waist_cm",
            "chest_cm",
            "hip_cm",
            "body_fat_pct",
            "notes",
        ]
        widgets = {
            "measured_on": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        numeric_fields = ["weight_kg", "waist_cm", "chest_cm", "hip_cm", "body_fat_pct"]
        for field in numeric_fields:
            value = cleaned.get(field)
            if value is not None and value < 0:
                self.add_error(field, "Value must be non-negative.")
        return cleaned

