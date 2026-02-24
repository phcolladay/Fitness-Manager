from django.urls import path

from . import views

app_name = "goals"

urlpatterns = [
    path("", views.goal_list, name="list"),
    path("add/", views.goal_add, name="add"),
    path("<int:goal_id>/edit/", views.goal_edit, name="edit"),
    path("<int:goal_id>/delete/", views.goal_delete, name="delete"),
]
