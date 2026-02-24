from django.urls import path

from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.profile_edit, name="profile"),
    path("body-metrics/", views.body_metrics_list, name="body_metrics"),
    path("body-metrics/add/", views.body_metric_add, name="body_metrics_add"),
    path("body-metrics/<int:entry_id>/edit/", views.body_metric_edit, name="body_metrics_edit"),
    path("body-metrics/<int:entry_id>/delete/", views.body_metric_delete, name="body_metrics_delete"),
]

