from django.conf import settings
from django.contrib.auth import get_user_model
from apps.discussions.models import Topic
from apps.moderation.models import Report
from apps.notifications.models import Notification


def community_context(request):
    """Global context available across all templates."""
    User = get_user_model()
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
        "total_registered_members": User.objects.filter(is_active=True).count(),
        "vapid_public_key": getattr(settings, "VAPID_PUBLIC_KEY", ""),
    }

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        context["unread_notifications_count"] = Notification.objects.filter(
            recipient=user, is_read=False
        ).count()

        if getattr(user, "is_moderator", False):
            context["pending_reports_count"] = Report.objects.filter(
                status__in=[Report.Status.PENDING, Report.Status.UNDER_REVIEW]
            ).count()

    return context
