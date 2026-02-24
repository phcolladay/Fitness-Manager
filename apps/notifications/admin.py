from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("channel", "status", "created_at", "user", "message")
    list_filter = ("channel", "status", "user")

# Register your models here.
