from django.urls import path

from . import views

app_name = "workouts"

urlpatterns = [
    path("", views.home, name="home"),
    path("workouts/", views.workout_list, name="list"),
    path("workouts/add/", views.workout_add, name="add"),
    path("workouts/<int:workout_id>/", views.workout_detail, name="detail"),
    path("workouts/<int:workout_id>/exercise/add/", views.exercise_add, name="exercise_add"),
]
