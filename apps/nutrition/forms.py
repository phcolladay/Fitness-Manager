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


class WaterEntryForm(forms.ModelForm):
    class Meta:
        model = WaterEntry
        fields = ["amount_ml", "consumed_at"]
        widgets = {"consumed_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}


class FoodLookupForm(forms.Form):
    query = forms.CharField(max_length=150)


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
