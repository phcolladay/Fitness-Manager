from django import forms
from django.conf import settings

from .models import FoodEntry, FoodPhoto, WaterEntry


class FoodEntryForm(forms.ModelForm):
    class Meta:
        model = FoodEntry
        fields = [
            "name",
            "brand",
            "quantity",
            "unit",
            "calories",
            "protein_g",
            "carbs_g",
            "fat_g",
            "fiber_g",
            "sugar_g",
            "sodium_mg",
            "micronutrients",
            "consumed_at",
        ]
        widgets = {"consumed_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def clean(self):
        cleaned = super().clean()
        for field in [
            "quantity",
            "calories",
            "protein_g",
            "carbs_g",
            "fat_g",
            "fiber_g",
            "sugar_g",
            "sodium_mg",
        ]:
            value = cleaned.get(field)
            if value is not None and value < 0:
                self.add_error(field, "Value must be non-negative.")
        return cleaned


class WaterEntryForm(forms.ModelForm):
    unit = forms.ChoiceField(choices=[("ml", "Milliliters (ml)"), ("oz", "Fluid ounces (oz)")], initial="ml")
    amount = forms.DecimalField(min_value=0, decimal_places=2, max_digits=7, help_text="Enter water amount.")

    class Meta:
        model = WaterEntry
        fields = ["consumed_at"]
        widgets = {"consumed_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["unit"].initial = "ml"
            self.fields["amount"].initial = self.instance.amount_ml

    def save(self, commit=True):
        entry = super().save(commit=False)
        amount = self.cleaned_data["amount"]
        unit = self.cleaned_data["unit"]
        if unit == "oz":
            entry.amount_ml = int(round(float(amount) * 29.5735))
        else:
            entry.amount_ml = int(round(float(amount)))
        if commit:
            entry.save()
        return entry


class FoodLookupForm(forms.Form):
    query = forms.CharField(max_length=150)


class FoodEstimateForm(forms.Form):
    description = forms.CharField(
        label="Meal Description / Ingredients",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "e.g. grilled chicken breast, brown rice, broccoli"}),
        max_length=1000,
    )


class FoodPhotoForm(forms.ModelForm):
    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image

        content_type = getattr(image, "content_type", "") or ""
        allowed = {"image/jpeg", "image/png", "image/webp"}
        if content_type and content_type not in allowed:
            raise forms.ValidationError("Only JPEG/PNG/WEBP images are allowed.")

        if image.size and image.size > settings.FOOD_PHOTO_MAX_UPLOAD_SIZE:
            raise forms.ValidationError("Image is too large (max 5MB).")

        try:
            from PIL import Image

            img = Image.open(image)
            img.verify()
            width, height = img.size
            if width > 8000 or height > 8000:
                raise forms.ValidationError("Image dimensions are too large.")
        except forms.ValidationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise forms.ValidationError("Please upload a valid image.") from exc
        finally:
            try:
                image.seek(0)
            except Exception:  # noqa: BLE001
                pass

        return image

    class Meta:
        model = FoodPhoto
        fields = ["image"]
