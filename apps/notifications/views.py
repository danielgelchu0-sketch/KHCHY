from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from .models import Notification


@method_decorator(login_required, name="dispatch")
class NotificationListView(View):
    """Member notification center displaying in-app updates."""

    def get(self, request):
        filter_type = request.GET.get("filter", "all")
        notifications_qs = Notification.objects.filter(recipient=request.user)

        if filter_type == "unread":
            notifications_qs = notifications_qs.filter(is_read=False)

        paginator = Paginator(notifications_qs, 20)
        page_obj = paginator.get_page(request.GET.get("page"))

        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

        return render(
            request,
            "notifications/notification_list.html",
            {
                "page_obj": page_obj,
                "filter_type": filter_type,
                "unread_count": unread_count,
            },
        )


@method_decorator(login_required, name="dispatch")
class NotificationMarkReadView(View):
    """Mark a notification as read and redirect to the target content."""

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])

        if request.headers.get("HX-Request"):
            return HttpResponse("")

        return redirect(notification.link)


@method_decorator(login_required, name="dispatch")
class NotificationMarkAllReadView(View):
    """Mark all unread notifications for the user as read."""

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")

        if request.headers.get("HX-Request"):
            return HttpResponse("<span class='notification-badge hidden' id='nav-notification-badge'>0</span>")

        return redirect("notifications:list")


@method_decorator(login_required, name="dispatch")
class NotificationBadgeView(View):
    """Endpoint for HTMX to fetch current unread count badge."""

    def get(self, request):
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        if unread_count > 0:
            html = f"<span class='notification-badge' id='nav-notification-badge'>{unread_count}</span>"
        else:
            html = "<span class='notification-badge hidden' id='nav-notification-badge'></span>"
        return HttpResponse(html)
