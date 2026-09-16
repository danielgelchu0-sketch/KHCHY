import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from apps.core.utils import sanitize_user_input
from .forms import DiscussionCreateForm, ReplyCreateForm, TopicAdminForm
from .models import Bookmark, Discussion, Reaction, Reply, Topic

logger = logging.getLogger(__name__)


class TopicListView(View):
    """Displays all topic rooms with active conversation statistics."""

    def get(self, request):
        topics = (
            Topic.objects.all()
            .annotate(
                discussions_count=Count(
                    "discussions",
                    filter=Q(discussions__is_deleted=False, discussions__status=Discussion.Status.ACTIVE),
                )
            )
            .order_by("order", "name")
        )

        recent_discussions = (
            Discussion.objects.filter(is_deleted=False, status=Discussion.Status.ACTIVE)
            .select_related("topic", "author", "author__profile")
            .order_by("-last_activity_at")[:8]
        )

        return render(
            request,
            "discussions/topic_list.html",
            {
                "topics": topics,
                "recent_discussions": recent_discussions,
            },
        )


class TopicDetailView(View):
    """Displays discussions inside a topic with pagination and sorting."""

    def get(self, request, slug):
        topic = get_object_or_404(Topic, slug=slug)
        sort_mode = request.GET.get("sort", "recent")

        discussions_qs = (
            Discussion.objects.filter(topic=topic, is_deleted=False)
            .exclude(status=Discussion.Status.HIDDEN)
            .select_related("topic", "author", "author__profile")
            .annotate(
                active_replies_count=Count("replies", filter=Q(replies__is_deleted=False, replies__status=Reply.Status.ACTIVE))
            )
        )

        if sort_mode == "newest":
            discussions_qs = discussions_qs.order_by("-created_at")
        elif sort_mode == "replies":
            discussions_qs = discussions_qs.order_by("-active_replies_count", "-last_activity_at")
        else:
            discussions_qs = discussions_qs.order_by("-last_activity_at")

        paginator = Paginator(discussions_qs, 20)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        return render(
            request,
            "discussions/topic_detail.html",
            {
                "topic": topic,
                "page_obj": page_obj,
                "sort_mode": sort_mode,
            },
        )


class DiscussionDetailView(View):
    """
    Displays the question, author details (anonymized for regular users if is_anonymous),
    and threaded replies.
    """

    def get(self, request, topic_slug, pk):
        topic = get_object_or_404(Topic, slug=topic_slug)
        discussion = get_object_or_404(
            Discussion.objects.select_related("author", "author__profile", "topic").annotate(
                _likes_count=Count(
                    "reactions",
                    filter=Q(reactions__vote_type=Reaction.VoteType.LIKE),
                    distinct=True,
                ),
                _dislikes_count=Count(
                    "reactions",
                    filter=Q(reactions__vote_type=Reaction.VoteType.DISLIKE),
                    distinct=True,
                ),
            ),
            pk=pk,
            topic=topic,
        )

        # Increment views safely
        Discussion.objects.filter(pk=pk).update(views_count=F("views_count") + 1)
        discussion.refresh_from_db(fields=["views_count"])

        # Fetch replies tree efficiently avoiding N+1 queries
        replies_qs = (
            Reply.objects.filter(discussion=discussion)
            .exclude(status=Reply.Status.HIDDEN)
            .select_related("author", "author__profile", "parent")
            .order_by("created_at")
        )

        # Build hierarchical reply structure
        replies_by_id = {}
        root_replies = []
        for r in replies_qs:
            replies_by_id[r.id] = r
            r.child_replies = []

        for r in replies_qs:
            if r.parent_id and r.parent_id in replies_by_id:
                replies_by_id[r.parent_id].child_replies.append(r)
            else:
                root_replies.append(r)

        # Check bookmark and reaction status if authenticated
        is_bookmarked = False
        user_reaction = None
        if request.user.is_authenticated:
            is_bookmarked = Bookmark.objects.filter(user=request.user, discussion=discussion).exists()
            user_reaction = discussion.get_user_reaction(request.user)

        reply_form = ReplyCreateForm()

        return render(
            request,
            "discussions/discussion_detail.html",
            {
                "topic": topic,
                "discussion": discussion,
                "root_replies": root_replies,
                "replies_count": len(replies_qs),
                "is_bookmarked": is_bookmarked,
                "user_reaction": user_reaction,
                "reply_form": reply_form,
            },
        )


@method_decorator(login_required, name="dispatch")
class DiscussionCreateView(View):
    """Allows authenticated members to post a new question/discussion."""

    def get(self, request, topic_slug):
        topic = get_object_or_404(Topic, slug=topic_slug, is_archived=False)
        form = DiscussionCreateForm()
        return render(request, "discussions/discussion_form.html", {"form": form, "topic": topic})

    def post(self, request, topic_slug):
        topic = get_object_or_404(Topic, slug=topic_slug, is_archived=False)

        if not request.user.can_post():
            messages.error(request, "Your account cannot currently post content.")
            return redirect(topic.get_absolute_url())

        form = DiscussionCreateForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data["title"]
            raw_content = form.cleaned_data["content"]
            post_mode = form.cleaned_data["post_mode"]
            is_anonymous = (post_mode == "anonymous")

            sanitized_content = sanitize_user_input(raw_content)

            with transaction.atomic():
                discussion = Discussion.objects.create(
                    topic=topic,
                    author=request.user,
                    title=title,
                    content=sanitized_content,
                    is_anonymous=is_anonymous,
                    status=Discussion.Status.ACTIVE,
                    last_activity_at=timezone.now(),
                )

            logger.info(
                f"Discussion created: '{discussion.title}' in '{topic.name}' by user {request.user.id} (Anonymous: {is_anonymous})"
            )
            messages.success(
                request,
                f"Your question has been posted {'anonymously' if is_anonymous else 'with your identity'}.",
            )
            return redirect(discussion.get_absolute_url())

        return render(request, "discussions/discussion_form.html", {"form": form, "topic": topic})


@method_decorator(login_required, name="dispatch")
class ReplyCreateView(View):
    """
    Submits a reply to a discussion or a nested reply to another reply.
    Supports regular submission and HTMX inline updates.
    """

    def post(self, request, topic_slug, pk):
        topic = get_object_or_404(Topic, slug=topic_slug)
        discussion = get_object_or_404(Discussion, pk=pk, topic=topic)

        if not discussion.can_user_reply(request.user):
            return HttpResponseForbidden("You cannot reply to this discussion at this time.")

        form = ReplyCreateForm(request.POST)
        if form.is_valid():
            raw_content = form.cleaned_data["content"]
            parent_reply = form.cleaned_data["parent_id"]
            post_mode = form.cleaned_data["post_mode"]
            is_anonymous = (post_mode == "anonymous")

            sanitized_content = sanitize_user_input(raw_content)

            with transaction.atomic():
                reply = Reply.objects.create(
                    discussion=discussion,
                    parent=parent_reply,
                    author=request.user,
                    content=sanitized_content,
                    is_anonymous=is_anonymous,
                    status=Reply.Status.ACTIVE,
                )
                discussion.last_activity_at = timezone.now()
                discussion.save(update_fields=["last_activity_at"])

            # Create notifications for relevant users
            from apps.notifications.services import create_reply_notifications
            create_reply_notifications(reply)

            logger.info(
                f"Reply created on discussion {discussion.id} by user {request.user.id} (Anonymous: {is_anonymous})"
            )

            # HTMX dynamic response handling
            if request.headers.get("HX-Request"):
                reply.child_replies = []
                return render(
                    request,
                    "discussions/partials/reply_card.html",
                    {
                        "reply": reply,
                        "discussion": discussion,
                    },
                )

            messages.success(
                request,
                f"Your reply has been posted {'anonymously' if is_anonymous else 'with your identity'}.",
            )
            return redirect(f"{discussion.get_absolute_url()}#reply-{reply.id}")

        # If invalid HTMX request, render error notification
        if request.headers.get("HX-Request"):
            return HttpResponse(
                f"<div class='alert alert-danger'>Unable to post reply: {form.errors.as_text()}</div>",
                status=400,
            )

        messages.error(request, "Please check your reply and try again.")
        return redirect(discussion.get_absolute_url())


@method_decorator(login_required, name="dispatch")
class DiscussionEditView(View):
    """Allows author or moderator to edit discussion text."""

    def get(self, request, topic_slug, pk):
        topic = get_object_or_404(Topic, slug=topic_slug)
        discussion = get_object_or_404(Discussion, pk=pk, topic=topic)

        if not discussion.can_user_edit(request.user):
            return HttpResponseForbidden("You are not authorized to edit this discussion.")

        form = DiscussionCreateForm(
            initial={
                "title": discussion.title,
                "content": discussion.content,
                "post_mode": "anonymous" if discussion.is_anonymous else "identified",
            }
        )
        return render(
            request,
            "discussions/discussion_edit.html",
            {"form": form, "discussion": discussion, "topic": topic},
        )

    def post(self, request, topic_slug, pk):
        topic = get_object_or_404(Topic, slug=topic_slug)
        discussion = get_object_or_404(Discussion, pk=pk, topic=topic)

        if not discussion.can_user_edit(request.user):
            return HttpResponseForbidden("You are not authorized to edit this discussion.")

        form = DiscussionCreateForm(request.POST)
        if form.is_valid():
            discussion.title = form.cleaned_data["title"]
            discussion.content = sanitize_user_input(form.cleaned_data["content"])
            post_mode = form.cleaned_data["post_mode"]
            discussion.is_anonymous = (post_mode == "anonymous")
            discussion.save()

            messages.success(request, "Your discussion has been updated.")
            return redirect(discussion.get_absolute_url())

        return render(
            request,
            "discussions/discussion_edit.html",
            {"form": form, "discussion": discussion, "topic": topic},
        )


@method_decorator(login_required, name="dispatch")
class DiscussionDeleteView(View):
    """Performs soft deletion of a discussion."""

    def post(self, request, topic_slug, pk):
        topic = get_object_or_404(Topic, slug=topic_slug)
        discussion = get_object_or_404(Discussion, pk=pk, topic=topic)

        if not discussion.can_user_delete(request.user):
            return HttpResponseForbidden("You are not authorized to delete this discussion.")

        discussion.is_deleted = True
        discussion.deleted_at = timezone.now()
        discussion.deleted_by = request.user
        discussion.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

        messages.success(request, "The discussion was deleted.")
        return redirect(topic.get_absolute_url())


@method_decorator(login_required, name="dispatch")
class ReplyDeleteView(View):
    """Performs soft deletion of a reply."""

    def post(self, request, pk):
        reply = get_object_or_404(Reply, pk=pk)

        if not reply.can_user_delete(request.user):
            return HttpResponseForbidden("You are not authorized to delete this reply.")

        reply.is_deleted = True
        reply.deleted_at = timezone.now()
        reply.deleted_by = request.user
        reply.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

        messages.success(request, "The reply was deleted.")
        return redirect(reply.discussion.get_absolute_url())


@method_decorator(login_required, name="dispatch")
class BookmarkToggleView(View):
    """Toggles bookmark/following status on a discussion."""

    def post(self, request, pk):
        discussion = get_object_or_404(Discussion, pk=pk)
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, discussion=discussion)

        if not created:
            bookmark.delete()
            is_bookmarked = False
            msg = "Removed from followed discussions."
        else:
            is_bookmarked = True
            msg = "Discussion bookmarked! You will receive notifications when new replies are posted."

        if request.headers.get("HX-Request"):
            return render(
                request,
                "discussions/partials/bookmark_button.html",
                {"discussion": discussion, "is_bookmarked": is_bookmarked},
            )

        messages.info(request, msg)
        return redirect(discussion.get_absolute_url())


@method_decorator(login_required, name="dispatch")
class ReactionToggleView(View):
    """
    Handles user reactions (like or dislike) on a discussion.
    - If user clicks the same reaction they currently have, remove it (toggle off).
    - If user clicks the opposite reaction, switch to that reaction.
    - If user has no existing reaction, create it.
    Supports HTMX partial rendering or standard HTTP redirects.
    """

    def post(self, request, pk, vote_type=None):
        discussion = get_object_or_404(Discussion, pk=pk)

        if not request.user.can_post():
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden("Your account is not permitted to react.")
            messages.error(request, "Your account cannot react to discussions.")
            return redirect(discussion.get_absolute_url())

        if discussion.is_deleted:
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden("Cannot react to a deleted discussion.")
            messages.error(request, "Cannot react to a deleted discussion.")
            return redirect(discussion.get_absolute_url())

        vote = vote_type or request.POST.get("vote_type")
        if vote not in (Reaction.VoteType.LIKE, Reaction.VoteType.DISLIKE):
            if request.headers.get("HX-Request"):
                return HttpResponseBadRequest("Invalid reaction type.")
            return redirect(discussion.get_absolute_url())

        reaction = Reaction.objects.filter(user=request.user, discussion=discussion).first()

        if reaction:
            if reaction.vote_type == vote:
                reaction.delete()
                current_reaction = None
                msg = f"Removed your {vote}."
            else:
                reaction.vote_type = vote
                reaction.save(update_fields=["vote_type", "updated_at"])
                current_reaction = vote
                msg = f"Changed reaction to {vote}."
        else:
            Reaction.objects.create(user=request.user, discussion=discussion, vote_type=vote)
            current_reaction = vote
            msg = f"Added {vote}."

        # Clear any cached reaction properties on the discussion instance
        if hasattr(discussion, "_likes_count"):
            delattr(discussion, "_likes_count")
        if hasattr(discussion, "_dislikes_count"):
            delattr(discussion, "_dislikes_count")
        if hasattr(discussion, "_user_reaction"):
            delattr(discussion, "_user_reaction")

        if request.headers.get("HX-Request"):
            return render(
                request,
                "discussions/partials/reaction_buttons.html",
                {
                    "discussion": discussion,
                    "user_reaction": current_reaction,
                    "user": request.user,
                },
            )

        messages.info(request, msg)
        return redirect(discussion.get_absolute_url())


@method_decorator(login_required, name="dispatch")
class ReplyEditView(View):
    """Allows author or moderator to edit a reply."""

    def get(self, request, pk):
        reply = get_object_or_404(Reply, pk=pk)
        if not reply.can_user_edit(request.user):
            return HttpResponseForbidden("You are not authorized to edit this reply.")

        form = ReplyCreateForm(
            initial={
                "content": reply.content,
                "post_mode": "anonymous" if reply.is_anonymous else "identified",
            }
        )
        return render(
            request,
            "discussions/reply_edit.html",
            {
                "form": form,
                "reply": reply,
                "discussion": reply.discussion,
            },
        )

    def post(self, request, pk):
        reply = get_object_or_404(Reply, pk=pk)
        if not reply.can_user_edit(request.user):
            return HttpResponseForbidden("You are not authorized to edit this reply.")

        form = ReplyCreateForm(request.POST)
        if form.is_valid():
            reply.content = sanitize_user_input(form.cleaned_data["content"])
            post_mode = form.cleaned_data["post_mode"]
            reply.is_anonymous = (post_mode == "anonymous")
            reply.save(update_fields=["content", "is_anonymous", "updated_at"])

            messages.success(request, "Your reply has been updated.")
            return redirect(f"{reply.discussion.get_absolute_url()}#reply-{reply.id}")

        return render(
            request,
            "discussions/reply_edit.html",
            {
                "form": form,
                "reply": reply,
                "discussion": reply.discussion,
            },
        )
