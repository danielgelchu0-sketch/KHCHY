import json
import logging
import os
import threading
import time
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from apps.discussions.models import Bookmark
from .models import Notification, PushSubscription

logger = logging.getLogger(__name__)


def _send_push_worker(user_ids, title, message, url):
    """
    Background worker thread that dispatches Web Push payloads
    via standard VAPID without blocking web request handling.
    """
    try:
        from pywebpush import webpush, WebPushException
        import requests
    except ImportError:
        logger.warning("pywebpush not installed. Web push dispatch skipped.")
        return

    try:
        vapid_private_key = getattr(settings, "VAPID_PRIVATE_KEY", None)
        claims_email = getattr(settings, "VAPID_CLAIMS_EMAIL", "admin@community.hkhc.org")
        if not vapid_private_key:
            logger.debug("No VAPID_PRIVATE_KEY configured. Push dispatch skipped.")
            return

        # Check for PythonAnywhere outbound proxy
        proxy_url = getattr(settings, "PYTHONANYWHERE_PROXY", "")
        session = requests.Session()
        if proxy_url:
            session.proxies = {"http": proxy_url, "https": proxy_url}

        subscriptions = list(PushSubscription.objects.filter(user_id__in=user_ids))
        if not subscriptions:
            return

        payload = json.dumps({
            "title": title,
            "message": message,
            "url": url,
            "icon": "/static/img/logo.png",
            "badge": "/static/img/logo.png",
            "timestamp": int(time.time()),
        })

        for sub in subscriptions:
            try:
                sub_info = {
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth,
                    },
                }
                webpush(
                    subscription_info=sub_info,
                    data=payload,
                    vapid_private_key=vapid_private_key,
                    vapid_claims={"sub": f"mailto:{claims_email}"},
                    timeout=5,
                    requests_session=session,
                )
            except WebPushException as ex:
                # 404 or 410 indicates the client subscription has expired or was revoked
                if ex.response is not None and ex.response.status_code in (404, 410):
                    logger.info(f"Purging expired push subscription {sub.id}")
                    try:
                        sub.delete()
                    except Exception:
                        pass
                else:
                    logger.warning(f"Push delivery warning for sub {sub.id}: {ex}")
            except Exception as ex:
                logger.warning(f"Push delivery error for sub {sub.id}: {ex}")
    except Exception as ex:
        logger.debug(f"Push worker exception: {ex}")
    finally:
        try:
            connection.close()
        except Exception:
            pass





def send_web_push(user_ids, title, message, url):
    """
    Dispatches web push notifications asynchronously in a background thread
    to guarantee <100ms response time on PythonAnywhere WSGI workers.
    """
    if not user_ids:
        return
    thread = threading.Thread(
        target=_send_push_worker,
        args=(list(user_ids), title, message, url),
        daemon=True,
    )
    thread.start()


def create_reply_notifications(reply):
    """
    Dispatch notifications when a reply is posted:
    1. To the discussion author (if not the reply author)
    2. To the parent reply author (if nested reply and not the reply author)
    3. To users who bookmarked/follow the discussion (excluding already notified)

    Respects privacy:
    If the reply is anonymous, the notification explicitly uses "A community member"
    to ensure the author's identity is never leaked through notification messages.
    """
    discussion = reply.discussion
    actor_label = "A community member" if reply.is_anonymous else reply.author.display_name
    discussion_url = f"{discussion.get_absolute_url()}#reply-{reply.id}"

    notified_user_ids = {reply.author_id}
    push_recipients = set()

    # 1. If replying to a parent reply
    if reply.parent and reply.parent.author_id not in notified_user_ids:
        parent_author = reply.parent.author
        Notification.objects.create(
            recipient=parent_author,
            notification_type=Notification.NotificationType.REPLY_COMMENT,
            title="New Reply to Your Comment",
            message=f"{actor_label} replied to your comment in '{discussion.title}'.",
            link=discussion_url,
        )
        notified_user_ids.add(parent_author.id)
        push_recipients.add(parent_author.id)

    # 2. To the original discussion / question author
    if discussion.author_id not in notified_user_ids:
        Notification.objects.create(
            recipient=discussion.author,
            notification_type=Notification.NotificationType.REPLY_QUESTION,
            title="New Answer to Your Question",
            message=f"{actor_label} shared an answer to your question '{discussion.title}'.",
            link=discussion_url,
        )
        notified_user_ids.add(discussion.author_id)
        push_recipients.add(discussion.author_id)

    # 3. To bookmarked/followers
    bookmarked_users = (
        Bookmark.objects.filter(discussion=discussion)
        .exclude(user_id__in=notified_user_ids)
        .select_related("user")
    )
    new_notifications = [
        Notification(
            recipient=b.user,
            notification_type=Notification.NotificationType.BOOKMARK_UPDATE,
            title="Update in Followed Discussion",
            message=f"New response added in '{discussion.title}'.",
            link=discussion_url,
        )
        for b in bookmarked_users
    ]
    if new_notifications:
        Notification.objects.bulk_create(new_notifications)
        for b in bookmarked_users:
            push_recipients.add(b.user_id)

    # Dispatch Web Push notifications to active subscriptions
    if push_recipients:
        snippet = reply.content[:100] + ("..." if len(reply.content) > 100 else "")
        send_web_push(
            user_ids=push_recipients,
            title=f"💬 {discussion.title[:50]}",
            message=f"{actor_label}: {snippet}",
            url=discussion_url,
        )


def create_discussion_notifications(discussion):
    """
    Broadcast notification to all registered active members when a new
    discussion/question is posted (Telegram-style channel broadcast).

    Respects privacy:
    If the question is anonymous, the notification uses 'A community member'
    so author identity is strictly protected.
    """
    User = get_user_model()
    actor_label = "A community member" if discussion.is_anonymous else discussion.author.display_name
    discussion_url = discussion.get_absolute_url()

    # Broadcast to all registered active members except the author
    recipients = list(User.objects.filter(is_active=True).exclude(id=discussion.author_id))
    if not recipients:
        return

    notifications = [
        Notification(
            recipient=user,
            notification_type=Notification.NotificationType.NEW_DISCUSSION,
            title=f"New Question in #{discussion.topic.name}",
            message=f"{actor_label} asked: '{discussion.title}'",
            link=discussion_url,
        )
        for user in recipients
    ]
    Notification.objects.bulk_create(notifications)

    # Dispatch Web Push
    recipient_ids = [u.id for u in recipients]
    send_web_push(
        user_ids=recipient_ids,
        title=f"📢 #{discussion.topic.name}",
        message=f"{actor_label}: {discussion.title}",
        url=discussion_url,
    )
