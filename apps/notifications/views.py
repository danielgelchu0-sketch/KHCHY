import json
import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from .models import Notification, PushSubscription

logger = logging.getLogger(__name__)


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


@method_decorator(login_required, name="dispatch")
class NotificationPollRecentView(View):
    """
    Near real-time endpoint for active tabs to fetch latest unread count
    and recent notification events to trigger Telegram-style in-tab toasts & audio chimes.
    """

    def get(self, request):
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

        since_id_raw = request.GET.get("since_id")
        notifications_qs = Notification.objects.filter(recipient=request.user)

        if since_id_raw and since_id_raw.isdigit():
            since_id = int(since_id_raw)
            recent_items = notifications_qs.filter(id__gt=since_id).order_by("-id")[:5]
        else:
            recent_items = notifications_qs.filter(is_read=False).order_by("-id")[:3]

        data = [
            {
                "id": notif.id,
                "title": notif.title,
                "message": notif.message,
                "link": notif.link,
                "notification_type": notif.notification_type,
                "created_at": notif.created_at.strftime("%I:%M %p"),
            }
            for notif in recent_items
        ]

        return JsonResponse({
            "unread_count": unread_count,
            "notifications": data,
        })


class PushPublicKeyView(View):
    """Returns the application VAPID public key for browser push registration."""

    def get(self, request):
        key = getattr(settings, "VAPID_PUBLIC_KEY", "")
        return JsonResponse({"publicKey": key})


@method_decorator(login_required, name="dispatch")
class PushSubscribeView(View):
    """Registers or updates a browser Web Push subscription for the authenticated user."""

    def post(self, request):
        try:
            body = json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return HttpResponseBadRequest("Invalid JSON payload")

        endpoint = body.get("endpoint")
        keys = body.get("keys", {})
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")

        if not endpoint or not p256dh or not auth:
            return HttpResponseBadRequest("Missing required push subscription fields")

        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

        sub, created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": user_agent,
            },
        )

        logger.info(f"Push subscription {'created' if created else 'updated'} for user {request.user.id}")
        return JsonResponse({"status": "subscribed", "id": sub.id})


@method_decorator(login_required, name="dispatch")
class PushUnsubscribeView(View):
    """Revokes a browser Web Push subscription."""

    def post(self, request):
        try:
            body = json.loads(request.body.decode("utf-8"))
            endpoint = body.get("endpoint")
        except Exception:
            endpoint = None

        if endpoint:
            deleted_count, _ = PushSubscription.objects.filter(
                user=request.user,
                endpoint=endpoint,
            ).delete()
            return JsonResponse({"status": "unsubscribed", "deleted": deleted_count})

        # If no specific endpoint provided, delete all subscriptions for this user
        deleted_count, _ = PushSubscription.objects.filter(user=request.user).delete()
        return JsonResponse({"status": "unsubscribed", "deleted": deleted_count})


class ServiceWorkerView(View):
    """Serves the Service Worker file at root scope."""

    def get(self, request):
        sw_code = """/**
 * HKHC Community Discussion Platform - Web Push Service Worker
 */

self.addEventListener('install', function(event) {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('push', function(event) {
    let payload = {};
    if (event.data) {
        try {
            payload = event.data.json();
        } catch (e) {
            payload = { message: event.data.text() };
        }
    }

    const title = payload.title || 'HKHC Community';
    const message = payload.message || 'New community message received.';
    const url = payload.url || '/';

    const options = {
        body: message,
        icon: payload.icon || '/static/img/logo.png',
        badge: payload.badge || '/static/img/logo.png',
        data: { url: url },
        vibrate: [150, 80, 150],
        renotify: true,
        tag: 'hkhc-notification-' + Date.now(),
        actions: [
            { action: 'open', title: 'Open / ክፈት' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if (client.url.includes(targetUrl) && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
"""
        response = HttpResponse(sw_code, content_type="application/javascript")
        response["Service-Worker-Allowed"] = "/"
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
