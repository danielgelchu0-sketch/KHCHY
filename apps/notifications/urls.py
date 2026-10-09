from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("<int:pk>/mark-read/", views.NotificationMarkReadView.as_view(), name="mark_read"),
    path("mark-all-read/", views.NotificationMarkAllReadView.as_view(), name="mark_all_read"),
    path("badge/", views.NotificationBadgeView.as_view(), name="badge"),
    path("poll-recent/", views.NotificationPollRecentView.as_view(), name="poll_recent"),
    path("push-public-key/", views.PushPublicKeyView.as_view(), name="push_public_key"),
    path("push-subscribe/", views.PushSubscribeView.as_view(), name="push_subscribe"),
    path("push-unsubscribe/", views.PushUnsubscribeView.as_view(), name="push_unsubscribe"),
    path("sw.js", views.ServiceWorkerView.as_view(), name="service_worker"),
]
