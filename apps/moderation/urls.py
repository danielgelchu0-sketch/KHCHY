from django.urls import path
from . import views

app_name = "moderation"

urlpatterns = [
    path("report/", views.ReportSubmitView.as_view(), name="report_submit"),
    path("dashboard/", views.ModeratorDashboardView.as_view(), name="dashboard"),
    path("reports/<int:pk>/", views.ReportDetailView.as_view(), name="report_detail"),
    path("discussion/<int:pk>/moderate/", views.DiscussionModerationActionView.as_view(), name="discussion_moderate"),
    path("reply/<int:pk>/moderate/", views.ReplyModerationActionView.as_view(), name="reply_moderate"),
    path("user/<int:user_id>/sanction/", views.UserSanctionView.as_view(), name="user_sanction"),
    path("audit-logs/", views.AuditLogListView.as_view(), name="audit_log_list"),
]
