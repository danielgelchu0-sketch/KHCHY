from django.conf import settings
from apps.discussions.models import Topic
from apps.moderation.models import Report
from apps.notifications.models import Notification


def community_context(request):
    """Global context available across all templates."""
    context = {
        "COMMUNITY_NAME": getattr(settings, "COMMUNITY_NAME", "HKHC Community"),
        "COMMUNITY_DESCRIPTION": getattr(
            settings,
            "COMMUNITY_DESCRIPTION",
            "A safe, moderated church community space for honest questions, biblical fellowship, and thoughtful discussion.",
        ),
        "nav_topics": Topic.objects.filter(is_archived=False).order_by("order", "name")[:8],
        "unread_notifications_count": 0,
        "pending_reports_count": 0,
    }

    if request.user.is_authenticated:
        context["unread_notifications_count"] = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()

        if request.user.is_moderator:
            context["pending_reports_count"] = Report.objects.filter(
                status__in=[Report.Status.PENDING, Report.Status.UNDER_REVIEW]
            ).count()

    return context
