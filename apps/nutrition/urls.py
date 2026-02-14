from django.urls import path

from . import views

app_name = "nutrition"

urlpatterns = [
    path("", views.food_list, name="list"),
    path("add/", views.food_add, name="add"),
    path("lookup/", views.food_lookup, name="lookup"),
    path("photo/", views.food_photo_upload, name="photo_upload"),
    path("water/", views.water_list, name="water_list"),
    path("water/add/", views.water_add, name="water_add"),
]
