from django.urls import path

from . import views

app_name = "workouts"

urlpatterns = [
    path("", views.home, name="home"),
    path("workouts/", views.workout_list, name="list"),
    path("workouts/add/", views.workout_add, name="add"),
    path("workouts/<int:workout_id>/edit/", views.workout_edit, name="edit"),
    path("workouts/<int:workout_id>/delete/", views.workout_delete, name="delete"),
    path("workouts/<int:workout_id>/", views.workout_detail, name="detail"),
    path("workouts/<int:workout_id>/exercise/add/", views.exercise_add, name="exercise_add"),
    path("workouts/<int:workout_id>/exercise/<int:exercise_id>/edit/", views.exercise_edit, name="exercise_edit"),
    path(
        "workouts/<int:workout_id>/exercise/<int:exercise_id>/delete/",
        views.exercise_delete,
        name="exercise_delete",
    ),
    path("exercise-library/", views.exercise_library, name="exercise_library"),
    path("plans/", views.plan_list, name="plan_list"),
    path("plans/add/", views.plan_add, name="plan_add"),
    path("plans/<int:plan_id>/edit/", views.plan_edit, name="plan_edit"),
    path("plans/<int:plan_id>/delete/", views.plan_delete, name="plan_delete"),
]
