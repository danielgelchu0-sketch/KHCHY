from django.conf import settings
from django.db import models
from django.utils import timezone


class Report(models.Model):
    """
    User report against inappropriate or safety-concerning content or behavior.
    """

    class Category(models.TextChoices):
        HARASSMENT = "harassment", "Harassment or Bullying"
        HATE = "hate", "Hate or Abusive Content"
        SEXUAL = "sexual", "Sexual or Inappropriate Content"
        THREATS = "threats", "Threats or Violence"
        SPAM = "spam", "Spam or Advertising"
        MISINFORMATION = "misinformation", "Misinformation or False Teaching"
        SELF_HARM = "self_harm", "Self-Harm or Safety Concern"
        OTHER = "other", "Other Community Concern"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Review"
        UNDER_REVIEW = "under_review", "Under Review"
        RESOLVED = "resolved", "Resolved (Action Taken)"
        DISMISSED = "dismissed", "Dismissed (No Violation)"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_submitted",
    )

    # Specific relational targets for integrity and speed
    target_discussion = models.ForeignKey(
        "discussions.Discussion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
    )
    target_reply = models.ForeignKey(
        "discussions.Reply",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports_against",
    )

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        db_index=True,
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Provide context to assist moderators in evaluating the report.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports_reviewed",
    )
    resolution_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Content Report"
        verbose_name_plural = "Content Reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"Report #{self.id} ({self.get_category_display()}) - {self.get_status_display()}"

    def get_target_repr(self):
        if self.target_discussion:
            return f"Discussion: '{self.target_discussion.title}'"
        if self.target_reply:
            return f"Reply #{self.target_reply.id} in '{self.target_reply.discussion.title}'"
        if self.target_user:
            return f"User Profile: {self.target_user.display_name}"
        return "Unknown Target"

    def get_target_internal_author(self):
        """Returns the real author user object for authorized moderator inspection."""
        if self.target_discussion:
            return self.target_discussion.author
        if self.target_reply:
            return self.target_reply.author
        if self.target_user:
            return self.target_user
        return None


class AuditLog(models.Model):
    """
    Immutable audit log for all sensitive moderation and administrative interventions.
    """

    class ActionType(models.TextChoices):
        HIDE_DISCUSSION = "hide_discussion", "Hide Discussion"
        RESTORE_DISCUSSION = "restore_discussion", "Restore Discussion"
        LOCK_DISCUSSION = "lock_discussion", "Lock Discussion"
        UNLOCK_DISCUSSION = "unlock_discussion", "Unlock Discussion"
        HIDE_REPLY = "hide_reply", "Hide Reply"
        RESTORE_REPLY = "restore_reply", "Restore Reply"
        WARN_USER = "warn_user", "Issue Warning to User"
        SUSPEND_USER = "suspend_user", "Suspend User Account"
        BAN_USER = "ban_user", "Ban User Account"
        UNBAN_USER = "unban_user", "Restore / Unban User Account"
        RESOLVE_REPORT = "resolve_report", "Resolve Report"
        DISMISS_REPORT = "dismiss_report", "Dismiss Report"
        ARCHIVE_TOPIC = "archive_topic", "Archive Topic Room"

    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="moderation_actions_taken",
    )
    action = models.CharField(max_length=30, choices=ActionType.choices, db_index=True)
    target_repr = models.CharField(max_length=255)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="moderation_actions_received",
    )
    reason = models.TextField(help_text="Detailed justification for the moderation action.")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Moderation Audit Log"
        verbose_name_plural = "Moderation Audit Logs"
        ordering = ["-created_at"]

    def __str__(self):
        mod_name = self.moderator.display_name if self.moderator else "System"
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {mod_name}: {self.get_action_display()} -> {self.target_repr}"
