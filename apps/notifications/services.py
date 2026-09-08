from django.urls import reverse
from apps.discussions.models import Bookmark
from .models import Notification


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

    # 3. To bookmarked/followers
    bookmarked_users = Bookmark.objects.filter(discussion=discussion).exclude(user_id__in=notified_user_ids).select_related("user")
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
