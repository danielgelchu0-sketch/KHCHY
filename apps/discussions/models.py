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



REACTION_CONFIG = [
    {"type": "like", "emoji": "👍", "label_en": "Like", "label_am": "ድጋፍ"},
    {"type": "love", "emoji": "❤️", "label_en": "Love", "label_am": "ፍቅር"},
    {"type": "amen", "emoji": "🙏", "label_en": "Amen", "label_am": "አሜን"},
    {"type": "insight", "emoji": "💡", "label_en": "Insight", "label_am": "ብርሃን"},
    {"type": "fellowship", "emoji": "🤝", "label_en": "Fellowship", "label_am": "ህብረት"},
    {"type": "comfort", "emoji": "😢", "label_en": "Comfort", "label_am": "ማጽናናት"},
]
REACTION_EMOJIS = {cfg["type"]: cfg["emoji"] for cfg in REACTION_CONFIG}


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

    @property
    def likes_count(self):
        if hasattr(self, "_likes_count"):
            return self._likes_count
        return self.reactions.filter(vote_type="like").count()

    @property
    def dislikes_count(self):
        if hasattr(self, "_dislikes_count"):
            return self._dislikes_count
        return self.reactions.filter(vote_type="dislike").count()
    def get_reaction_counts(self, user=None):
        """Returns list of active reaction badges with counts and current user's reaction."""
        if hasattr(self, "_reaction_counts"):
            counts = self._reaction_counts
        else:
            counts = dict(
                self.reactions.values("vote_type").annotate(count=models.Count("id")).values_list("vote_type", "count")
            )
        user_reaction = self.get_user_reaction(user) if user and user.is_authenticated else None

        active_badges = []
        for cfg in REACTION_CONFIG:
            v_type = cfg["type"]
            c = counts.get(v_type, 0)
            if c > 0:
                active_badges.append({
                    "type": v_type,
                    "emoji": cfg["emoji"],
                    "label_en": cfg["label_en"],
                    "label_am": cfg["label_am"],
                    "count": c,
                    "is_active": (user_reaction == v_type),
                })
        if counts.get("dislike", 0) > 0:
            active_badges.append({
                "type": "dislike",
                "emoji": "👎",
                "label_en": "Dislike",
                "label_am": "አልተስማማሁም",
                "count": counts["dislike"],
                "is_active": (user_reaction == "dislike"),
            })
        return active_badges

    def get_user_reaction(self, user):
        if hasattr(self, "_user_reaction"):
            return self._user_reaction
        if not user or not user.is_authenticated:
            return None
        reaction = self.reactions.filter(user=user).first()
        return reaction.vote_type if reaction else None


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

    @property
    def likes_count(self):
        if hasattr(self, "_likes_count"):
            return self._likes_count
        return self.reactions.filter(vote_type="like").count()

    @property
    def dislikes_count(self):
        if hasattr(self, "_dislikes_count"):
            return self._dislikes_count
        return self.reactions.filter(vote_type="dislike").count()

    def get_reaction_counts(self, user=None):
        """Returns list of active reaction badges with counts and current user's reaction for this reply."""
        if hasattr(self, "_reaction_counts"):
            counts = self._reaction_counts
        else:
            counts = dict(
                self.reactions.values("vote_type").annotate(count=models.Count("id")).values_list("vote_type", "count")
            )
        user_reaction = self.get_user_reaction(user) if user and user.is_authenticated else None

        active_badges = []
        for cfg in REACTION_CONFIG:
            v_type = cfg["type"]
            c = counts.get(v_type, 0)
            if c > 0:
                active_badges.append({
                    "type": v_type,
                    "emoji": cfg["emoji"],
                    "label_en": cfg["label_en"],
                    "label_am": cfg["label_am"],
                    "count": c,
                    "is_active": (user_reaction == v_type),
                })
        if counts.get("dislike", 0) > 0:
            active_badges.append({
                "type": "dislike",
                "emoji": "👎",
                "label_en": "Dislike",
                "label_am": "አልተስማማሁም",
                "count": counts["dislike"],
                "is_active": (user_reaction == "dislike"),
            })
        return active_badges

    def get_user_reaction(self, user):
        if hasattr(self, "_user_reaction"):
            return self._user_reaction
        if not user or not user.is_authenticated:
            return None
        reaction = self.reactions.filter(user=user).first()
        return reaction.vote_type if reaction else None


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


class Reaction(models.Model):
    """
    User reaction on a discussion.
    Each user can have at most one reaction per discussion.
    """

    class VoteType(models.TextChoices):
        LIKE = "like", "👍 Like"
        LOVE = "love", "❤️ Love"
        AMEN = "amen", "🙏 Amen"
        INSIGHT = "insight", "💡 Insight"
        FELLOWSHIP = "fellowship", "🤝 Fellowship"
        COMFORT = "comfort", "😢 Comfort"
        DISLIKE = "dislike", "Dislike"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussion_reactions",
    )
    discussion = models.ForeignKey(
        Discussion,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    vote_type = models.CharField(
        max_length=20,
        choices=VoteType.choices,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Discussion Reaction"
        verbose_name_plural = "Discussion Reactions"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "discussion"],
                name="unique_user_discussion_reaction",
            )
        ]
        indexes = [
            models.Index(fields=["discussion", "vote_type"]),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.vote_type} on '{self.discussion.title}'"


class ReplyReaction(models.Model):
    """
    User reaction on a reply.
    Each user can have at most one reaction per reply.
    """

    class VoteType(models.TextChoices):
        LIKE = "like", "👍 Like"
        LOVE = "love", "❤️ Love"
        AMEN = "amen", "🙏 Amen"
        INSIGHT = "insight", "💡 Insight"
        FELLOWSHIP = "fellowship", "🤝 Fellowship"
        COMFORT = "comfort", "😢 Comfort"
        DISLIKE = "dislike", "Dislike"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reply_reactions",
    )
    reply = models.ForeignKey(
        Reply,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    vote_type = models.CharField(
        max_length=20,
        choices=VoteType.choices,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reply Reaction"
        verbose_name_plural = "Reply Reactions"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "reply"],
                name="unique_user_reply_reaction",
            )
        ]
        indexes = [
            models.Index(fields=["reply", "vote_type"]),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.vote_type} on Reply {self.reply_id}"

