from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    In-app database notification notifying members of replies, comments,
    followed discussion activity, and moderation decisions.
    """

    class NotificationType(models.TextChoices):
        REPLY_QUESTION = "reply_question", "Reply to Your Question"
        REPLY_COMMENT = "reply_comment", "Reply to Your Comment"
        BOOKMARK_UPDATE = "bookmark_update", "New Reply in Followed Discussion"
        NEW_DISCUSSION = "new_discussion", "New Community Discussion"
        MODERATION = "moderation", "Moderation Notification"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.REPLY_QUESTION,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.email}: {self.title}"


class PushSubscription(models.Model):
    """
    Browser Web Push subscription credentials (VAPID endpoint & keys)
    for native device and lockscreen push notifications.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        db_index=True,
    )
    endpoint = models.URLField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Push Subscription"
        verbose_name_plural = "Push Subscriptions"
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"PushSubscription for {self.user.email} ({self.created_at:%Y-%m-%d})"

