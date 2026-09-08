import logging
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views import View

from apps.discussions.models import Discussion, Topic

logger = logging.getLogger(__name__)


class HomeView(View):
    """
    Public landing page for visitors.
    If already authenticated, redirects straight to topic discussion rooms.
    """

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("discussions:topic_list")

        topics = Topic.objects.filter(is_archived=False).order_by("order")[:6]
        return render(request, "core/home.html", {"featured_topics": topics})


class SearchView(View):
    """
    Community search engine across Topics, Discussion titles, and content.
    Excludes deleted or hidden items.
    """

    def get(self, request):
        query = request.GET.get("q", "").strip()
        results = []
        topics_matched = []

        if query:
            topics_matched = Topic.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            ).filter(is_archived=False)[:5]

            discussions_qs = (
                Discussion.objects.filter(
                    Q(title__icontains=query) | Q(content__icontains=query)
                )
                .filter(is_deleted=False)
                .exclude(status=Discussion.Status.HIDDEN)
                .select_related("topic", "author", "author__profile")
                .order_by("-last_activity_at")
            )

            paginator = Paginator(discussions_qs, 15)
            results = paginator.get_page(request.GET.get("page"))

        return render(
            request,
            "core/search.html",
            {
                "query": query,
                "results": results,
                "topics_matched": topics_matched,
            },
        )


class PrivacyPolicyView(View):
    """
    Truthful church community privacy disclosure explaining the two identity modes,
    moderator oversight for safety/abuse investigation, and data protection practices.
    """

    def get(self, request):
        return render(request, "core/privacy_policy.html")


class CommunityGuidelinesView(View):
    """
    Community guidelines emphasizing psychological safety, respectful dialogue,
    support for sensitive questions, and zero tolerance for harassment or doxxing.
    """

    def get(self, request):
        return render(request, "core/community_guidelines.html")


# Custom HTTP error views
def bad_request_view(request, exception=None):
    return render(request, "errors/400.html", status=400)


def permission_denied_view(request, exception=None):
    return render(request, "errors/403.html", status=403)


def page_not_found_view(request, exception=None):
    return render(request, "errors/404.html", status=404)


def server_error_view(request):
    return render(request, "errors/500.html", status=500)


def rate_limited_view(request, exception=None):
    return render(request, "errors/429.html", status=429)
