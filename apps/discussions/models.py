from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Topic(models.Model):
    """
    Topic rooms representing specific church community conversation categories.
    E.g., Faith & Spiritual Life, Youth Questions, Sexuality & Boundaries, Relationships.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(help_text="Clear guidance on what issues this room discusses.")
    icon = models.CharField(
        max_length=50,
        default="chat-bubble",
        help_text="Icon identifier for topic card presentation.",
    )
    order = models.PositiveIntegerField(default=0, help_text="Order in topic listings.")
    is_archived = models.BooleanField(
        default=False,
        help_text="Archived topics are read-only and hidden from active creation.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Discussion Topic"
        verbose_name_plural = "Discussion Topics"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("discussions:topic_detail", kwargs={"slug": self.slug})

    @property
    def active_discussions_count(self):
        return self.discussions.filter(is_deleted=False, status=Discussion.Status.ACTIVE).count()


class Discussion(models.Model):
    """
    Discussion thread / question started by a community member.
    Anonymity is decided by the author at time of posting.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        LOCKED = "locked", "Locked (No further replies allowed)"
        HIDDEN = "hidden", "Hidden by Moderation"

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="discussions")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussions",
        help_text="Internal authenticated author. Preserved for audit/safety.",
    )
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Question details or discussion background.")
    is_anonymous = models.BooleanField(
        default=False,
        db_index=True,
        help_text="When True, identity is strictly obscured from ordinary members.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="moderated_discussions",
    )
    views_count = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Discussion Thread"
        verbose_name_plural = "Discussion Threads"
        ordering = ["-last_activity_at"]
        indexes = [
            models.Index(fields=["topic", "-last_activity_at"]),
            models.Index(fields=["author", "-created_at"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("discussions:discussion_detail", kwargs={"topic_slug": self.topic.slug, "pk": self.pk})

    def get_display_author_for(self, viewing_user):
        """
        Privacy-safe author presentation.
        Never reveals author identity if is_anonymous=True unless viewing_user is a moderator/admin.
        """
        if self.is_deleted:
            return "Deleted"

        if self.is_anonymous:
            if viewing_user and viewing_user.is_authenticated and viewing_user.is_moderator:
                return f"Anonymous Member [Mod View: {self.author.display_name} ({self.author.email})]"
            return "Anonymous Member"
        return self.author.display_name

    def is_author_visible_for(self, viewing_user):
        """Returns True if the author's public identity can be displayed to viewing_user."""
        if not self.is_anonymous:
            return True
        return bool(viewing_user and viewing_user.is_authenticated and viewing_user.is_moderator)

    def can_user_edit(self, user):
        """Author can edit if active and not locked; moderators can edit."""
        if not user or not user.is_authenticated or self.is_deleted:
            return False
        if user.is_moderator:
            return True
        return self.author_id == user.id and self.status == self.Status.ACTIVE

    def can_user_delete(self, user):
        """Author or moderator can soft-delete."""
        if not user or not user.is_authenticated or self.is_deleted:
            return False
        if user.is_moderator:
            return True
        return self.author_id == user.id

    def can_user_reply(self, user):
        """Users can reply if discussion is active, not deleted, and topic not archived."""
        if not user or not user.is_authenticated:
            return False
        if not user.can_post():
            return False
        if self.topic.is_archived or self.is_deleted or self.status != self.Status.ACTIVE:
            return False
        return True


class Reply(models.Model):
    """
    Reply to a discussion question or a nested reply to another reply.
    Allows threaded conversations, answers, and debate.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        HIDDEN = "hidden", "Hidden by Moderation"

    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name="replies")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        help_text="Parent reply for nested threaded responses.",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="replies",
        help_text="Internal authenticated author.",
    )
    content = models.TextField()
    is_anonymous = models.BooleanField(
        default=False,
        db_index=True,
        help_text="When True, identity is strictly obscured from ordinary members.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="moderated_replies",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reply"
        verbose_name_plural = "Replies"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["discussion", "parent", "created_at"]),
        ]

    def __str__(self):
        return f"Reply by {self.author_id} on {self.discussion_id}"

    def get_display_author_for(self, viewing_user):
        """
        Privacy-safe author presentation for replies.
        Obscures identity if is_anonymous=True unless viewing_user is a moderator/admin.
        """
        if self.is_deleted:
            return "Deleted"

        if self.is_anonymous:
            if viewing_user and viewing_user.is_authenticated and viewing_user.is_moderator:
                return f"Anonymous Member [Mod View: {self.author.display_name} ({self.author.email})]"
            return "Anonymous Member"
        return self.author.display_name

    def is_author_visible_for(self, viewing_user):
        if not self.is_anonymous:
            return True
        return bool(viewing_user and viewing_user.is_authenticated and viewing_user.is_moderator)

    def can_user_edit(self, user):
        if not user or not user.is_authenticated or self.is_deleted:
            return False
        if user.is_moderator:
            return True
        return self.author_id == user.id and self.status == self.Status.ACTIVE

    def can_user_delete(self, user):
        if not user or not user.is_authenticated or self.is_deleted:
            return False
        if user.is_moderator:
            return True
        return self.author_id == user.id


class Bookmark(models.Model):
    """Allows members to follow/bookmark discussions to receive updates."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Discussion Bookmark"
        verbose_name_plural = "Discussion Bookmarks"
        constraints = [
            models.UniqueConstraint(fields=["user", "discussion"], name="unique_user_discussion_bookmark")
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.discussion.title}"
