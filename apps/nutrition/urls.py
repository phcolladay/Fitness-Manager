from django.urls import path

from . import views

app_name = "nutrition"

urlpatterns = [
    path("", views.food_list, name="list"),
    path("add/", views.food_add, name="add"),
    path("<int:entry_id>/edit/", views.food_edit, name="edit"),
    path("<int:entry_id>/delete/", views.food_delete, name="delete"),
    path("lookup/", views.food_lookup, name="lookup"),
    path("summary/", views.food_summary, name="summary"),
    path("photo/", views.food_photo_upload, name="photo_upload"),
    path("estimate/", views.food_estimate, name="estimate"),
    path("water/", views.water_list, name="water_list"),
    path("water/add/", views.water_add, name="water_add"),
    path("water/<int:entry_id>/edit/", views.water_edit, name="water_edit"),
    path("water/<int:entry_id>/delete/", views.water_delete, name="water_delete"),
]
