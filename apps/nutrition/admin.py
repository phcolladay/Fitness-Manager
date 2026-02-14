from django.contrib import admin

from .models import FoodEntry, FoodPhoto, WaterEntry


@admin.register(FoodEntry)
class FoodEntryAdmin(admin.ModelAdmin):
    list_display = ("name", "calories", "consumed_at", "source", "user")
    search_fields = ("name", "brand")
    list_filter = ("source", "user")


@admin.register(WaterEntry)
class WaterEntryAdmin(admin.ModelAdmin):
    list_display = ("amount_ml", "consumed_at", "user")


@admin.register(FoodPhoto)
class FoodPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_at", "user")

# Register your models here.
