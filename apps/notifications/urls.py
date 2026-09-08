from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("<int:pk>/mark-read/", views.NotificationMarkReadView.as_view(), name="mark_read"),
    path("mark-all-read/", views.NotificationMarkAllReadView.as_view(), name="mark_all_read"),
    path("badge/", views.NotificationBadgeView.as_view(), name="badge"),
]
