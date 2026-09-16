from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.discussions.models import Bookmark, Discussion, Reaction, Reply, ReplyReaction, Topic


User = get_user_model()


class DiscussionsTests(TestCase):
    """Test suite for discussion topics, threads, threaded replies, and bookmarks."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="author@example.com", password="Pass123!Password", display_name="Disc Author"
        )
        self.responder = User.objects.create_user(
            email="responder@example.com", password="Pass123!Password", display_name="Helper Member"
        )
        self.topic = Topic.objects.create(name="Faith Room", slug="faith-room", description="Faith discussions")
        self.discussion = Discussion.objects.create(
            topic=self.topic,
            author=self.user,
            title="How do we pray during difficult seasons?",
            content="Context about praying when life is hard...",
            is_anonymous=False,
        )

    def test_create_question_thread(self):
        """User can create a question in a topic."""
        self.client.force_login(self.user)
        create_url = reverse("discussions:discussion_create", kwargs={"topic_slug": self.topic.slug})
        response = self.client.post(create_url, {
            "title": "What does Scripture say about forgiveness?",
            "content": "Context and detailed question about forgiving those who wronged us...",
            "post_mode": "identified",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Discussion.objects.filter(title="What does Scripture say about forgiveness?").exists())

    def test_create_reply(self):
        """User can reply to a discussion thread."""
        self.client.force_login(self.responder)
        reply_url = reverse("discussions:reply_create", kwargs={"topic_slug": self.topic.slug, "pk": self.discussion.id})
        response = self.client.post(reply_url, {
            "content": "Here is a thoughtful answer with Psalm 23 reference.",
            "post_mode": "identified",
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        reply = Reply.objects.filter(discussion=self.discussion).first()
        self.assertIsNotNone(reply)
        self.assertEqual(reply.author, self.responder)
        self.assertIsNone(reply.parent)

    def test_create_nested_threaded_reply(self):
        """User can reply directly to another reply (nested thread)."""
        parent_reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="First tier answer.",
            is_anonymous=False,
        )
        self.client.force_login(self.user)
        reply_url = reverse("discussions:reply_create", kwargs={"topic_slug": self.topic.slug, "pk": self.discussion.id})
        response = self.client.post(reply_url, {
            "content": "Nested response debating or clarifying the parent answer.",
            "parent_id": parent_reply.id,
            "post_mode": "identified",
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        nested = Reply.objects.filter(parent=parent_reply).first()
        self.assertIsNotNone(nested)
        self.assertEqual(nested.parent, parent_reply)
        self.assertEqual(nested.author, self.user)

    def test_edit_own_discussion(self):
        """Author can edit their own active discussion."""
        self.client.force_login(self.user)
        edit_url = reverse("discussions:discussion_edit", kwargs={"topic_slug": self.topic.slug, "pk": self.discussion.id})
        response = self.client.post(edit_url, {
            "title": "Updated: How do we pray during difficult seasons?",
            "content": "Updated context about prayer...",
            "post_mode": "identified",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.discussion.refresh_from_db()
        self.assertEqual(self.discussion.title, "Updated: How do we pray during difficult seasons?")

    def test_soft_delete_discussion(self):
        """Deleting a discussion marks is_deleted=True without destroying the record."""
        self.client.force_login(self.user)
        delete_url = reverse("discussions:discussion_delete", kwargs={"topic_slug": self.topic.slug, "pk": self.discussion.id})
        response = self.client.post(delete_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.discussion.refresh_from_db()
        self.assertTrue(self.discussion.is_deleted)
        self.assertIsNotNone(self.discussion.deleted_at)
        self.assertEqual(self.discussion.deleted_by, self.user)

    def test_bookmark_follow_toggle(self):
        """User can bookmark/follow a discussion and toggle it off."""
        self.client.force_login(self.responder)
        bm_url = reverse("discussions:bookmark_toggle", kwargs={"pk": self.discussion.id})

        # Toggle on
        self.client.post(bm_url)
        self.assertTrue(Bookmark.objects.filter(user=self.responder, discussion=self.discussion).exists())

        # Toggle off
        self.client.post(bm_url)
        self.assertFalse(Bookmark.objects.filter(user=self.responder, discussion=self.discussion).exists())

    def test_discussion_pagination(self):
        """Topic page paginates discussions when count exceeds 20."""
        discussions = [
            Discussion(
                topic=self.topic,
                author=self.user,
                title=f"Question #{i}",
                content=f"Context for question #{i}...",
            )
            for i in range(25)
        ]
        Discussion.objects.bulk_create(discussions)

        response = self.client.get(self.topic.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["page_obj"].has_other_pages())
        self.assertEqual(len(response.context["page_obj"]), 20)

    def test_edit_own_reply(self):
        """Author can edit their own reply."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="Original reply text.",
            is_anonymous=False,
        )
        self.client.force_login(self.responder)
        edit_url = reverse("discussions:reply_edit", kwargs={"pk": reply.id})
        response = self.client.post(edit_url, {
            "content": "Updated reply text with more clarity.",
            "post_mode": "anonymous",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        reply.refresh_from_db()
        self.assertIn("Updated reply text with more clarity.", reply.content)
        self.assertTrue(reply.is_anonymous)

    def test_user_cannot_edit_another_users_reply(self):
        """User A cannot edit User B's reply."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="Original reply text.",
            is_anonymous=False,
        )
        self.client.force_login(self.user)
        edit_url = reverse("discussions:reply_edit", kwargs={"pk": reply.id})
        response = self.client.post(edit_url, {
            "content": "Hacked reply content.",
            "post_mode": "identified",
        })
        self.assertEqual(response.status_code, 403)
        reply.refresh_from_db()
        self.assertEqual(reply.content, "Original reply text.")

    def test_reaction_like_and_toggle_off(self):
        """User can like a discussion and toggle it off by liking again."""
        self.client.force_login(self.responder)
        react_url = reverse("discussions:reaction_toggle", kwargs={"pk": self.discussion.id})

        # Like the post
        response = self.client.post(react_url, {"vote_type": "like"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.discussion.likes_count, 1)
        self.assertEqual(self.discussion.dislikes_count, 0)
        self.assertEqual(self.discussion.get_user_reaction(self.responder), "like")

        # Like again -> toggles off
        response = self.client.post(react_url, {"vote_type": "like"})
        self.assertEqual(response.status_code, 302)
        # Refresh discussion
        self.discussion.refresh_from_db()
        self.assertEqual(self.discussion.likes_count, 0)
        self.assertEqual(self.discussion.dislikes_count, 0)
        self.assertIsNone(self.discussion.get_user_reaction(self.responder))

    def test_reaction_dislike_and_toggle_off(self):
        """User can dislike a discussion and toggle it off by disliking again."""
        self.client.force_login(self.responder)
        react_url = reverse("discussions:reaction_toggle", kwargs={"pk": self.discussion.id})

        # Dislike the post
        response = self.client.post(react_url, {"vote_type": "dislike"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.discussion.dislikes_count, 1)
        self.assertEqual(self.discussion.likes_count, 0)
        self.assertEqual(self.discussion.get_user_reaction(self.responder), "dislike")

        # Dislike again -> toggles off
        response = self.client.post(react_url, {"vote_type": "dislike"})
        self.assertEqual(response.status_code, 302)
        self.discussion.refresh_from_db()
        self.assertEqual(self.discussion.dislikes_count, 0)
        self.assertIsNone(self.discussion.get_user_reaction(self.responder))

    def test_reaction_switch_between_like_and_dislike(self):
        """User can switch reaction from like to dislike and vice-versa."""
        self.client.force_login(self.responder)
        react_url = reverse("discussions:reaction_toggle", kwargs={"pk": self.discussion.id})

        # First like
        self.client.post(react_url, {"vote_type": "like"})
        self.assertEqual(self.discussion.likes_count, 1)
        self.assertEqual(self.discussion.dislikes_count, 0)

        # Switch to dislike
        self.client.post(react_url, {"vote_type": "dislike"})
        self.discussion.refresh_from_db()
        self.assertEqual(self.discussion.likes_count, 0)
        self.assertEqual(self.discussion.dislikes_count, 1)
        self.assertEqual(self.discussion.get_user_reaction(self.responder), "dislike")

        # Switch back to like
        self.client.post(react_url, {"vote_type": "like"})
        self.discussion.refresh_from_db()
        self.assertEqual(self.discussion.likes_count, 1)
        self.assertEqual(self.discussion.dislikes_count, 0)
        self.assertEqual(self.discussion.get_user_reaction(self.responder), "like")

    def test_reaction_htmx_partial_response(self):
        """HTMX POST request receives the updated partial reaction buttons template."""
        self.client.force_login(self.responder)
        react_url = reverse("discussions:reaction_toggle", kwargs={"pk": self.discussion.id})

        response = self.client.post(react_url, {"vote_type": "like"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "discussions/partials/reaction_buttons.html")
        content = response.content.decode()
        self.assertIn("like-btn", content)
        self.assertIn("active", content)
        self.assertIn(react_url, content)

    def test_reaction_unauthenticated_user_redirected(self):
        """Unauthenticated user POST to reaction endpoint is redirected to login."""
        react_url = reverse("discussions:reaction_toggle", kwargs={"pk": self.discussion.id})
        response = self.client.post(react_url, {"vote_type": "like"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_reaction_suspended_user_forbidden(self):
        """Suspended user cannot react to discussions and is intercepted by middleware."""
        self.responder.status = User.AccountStatus.SUSPENDED
        self.responder.save()
        self.client.force_login(self.responder)
        react_url = reverse("discussions:reaction_toggle", kwargs={"pk": self.discussion.id})

        response = self.client.post(react_url, {"vote_type": "like"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        self.assertEqual(Reaction.objects.count(), 0)

    def test_reaction_deleted_discussion_forbidden(self):
        """Cannot react to a deleted discussion."""
        self.discussion.is_deleted = True
        self.discussion.save()
        self.client.force_login(self.responder)
        react_url = reverse("discussions:reaction_toggle", kwargs={"pk": self.discussion.id})

        response = self.client.post(react_url, {"vote_type": "like"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Reaction.objects.count(), 0)

    def test_reaction_invalid_vote_type(self):
        """Invalid vote type returns 400 Bad Request on HTMX or redirect on standard POST."""
        self.client.force_login(self.responder)
        react_url = reverse("discussions:reaction_toggle", kwargs={"pk": self.discussion.id})

        response = self.client.post(react_url, {"vote_type": "invalid_vote"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 400)

    def test_reaction_typed_url_pattern(self):
        """User can react using typed URL path pattern."""
        self.client.force_login(self.responder)
        react_url = reverse("discussions:reaction_toggle_typed", kwargs={"pk": self.discussion.id, "vote_type": "like"})

        response = self.client.post(react_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.discussion.likes_count, 1)

    def test_discussion_detail_renders_reaction_buttons(self):
        """Discussion detail template renders reaction buttons and counts."""
        # Authenticated view
        self.client.force_login(self.user)
        response = self.client.get(self.discussion.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "reaction-buttons-group")
        self.assertContains(response, "like-btn")
        self.assertContains(response, "dislike-btn")

        # Anonymous view
        self.client.logout()
        response = self.client.get(self.discussion.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "reaction-buttons-group")

    def test_reply_reaction_like_and_unlike(self):
        """User can like a reply and clicking again removes the like."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="This is an insightful answer.",
        )
        self.client.force_login(self.user)
        react_url = reverse("discussions:reply_reaction_toggle", kwargs={"pk": reply.id})

        # Like reply
        response = self.client.post(react_url, {"vote_type": "like"})
        self.assertEqual(response.status_code, 302)
        reply.refresh_from_db()
        self.assertEqual(reply.likes_count, 1)
        self.assertEqual(reply.dislikes_count, 0)
        self.assertEqual(reply.get_user_reaction(self.user), "like")

        # Like again -> removes like
        response = self.client.post(react_url, {"vote_type": "like"})
        self.assertEqual(response.status_code, 302)
        reply.refresh_from_db()
        self.assertEqual(reply.likes_count, 0)
        self.assertIsNone(reply.get_user_reaction(self.user))

    def test_reply_reaction_dislike_and_undislike(self):
        """User can dislike a reply and clicking again removes the dislike."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.user,
            content="Initial response.",
        )
        self.client.force_login(self.responder)
        react_url = reverse("discussions:reply_reaction_toggle", kwargs={"pk": reply.id})

        # Dislike reply
        response = self.client.post(react_url, {"vote_type": "dislike"})
        self.assertEqual(response.status_code, 302)
        reply.refresh_from_db()
        self.assertEqual(reply.dislikes_count, 1)
        self.assertEqual(reply.likes_count, 0)
        self.assertEqual(reply.get_user_reaction(self.responder), "dislike")

        # Dislike again -> toggles off
        response = self.client.post(react_url, {"vote_type": "dislike"})
        self.assertEqual(response.status_code, 302)
        reply.refresh_from_db()
        self.assertEqual(reply.dislikes_count, 0)
        self.assertIsNone(reply.get_user_reaction(self.responder))

    def test_reply_reaction_switch_between_like_and_dislike(self):
        """User can switch reaction on reply from like to dislike and vice-versa."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="Let's reflect on this verse.",
        )
        self.client.force_login(self.user)
        react_url = reverse("discussions:reply_reaction_toggle", kwargs={"pk": reply.id})

        # Like
        self.client.post(react_url, {"vote_type": "like"})
        reply.refresh_from_db()
        self.assertEqual(reply.likes_count, 1)
        self.assertEqual(reply.dislikes_count, 0)

        # Switch to dislike
        self.client.post(react_url, {"vote_type": "dislike"})
        reply.refresh_from_db()
        self.assertEqual(reply.likes_count, 0)
        self.assertEqual(reply.dislikes_count, 1)
        self.assertEqual(reply.get_user_reaction(self.user), "dislike")

        # Switch back to like
        self.client.post(react_url, {"vote_type": "like"})
        reply.refresh_from_db()
        self.assertEqual(reply.likes_count, 1)
        self.assertEqual(reply.dislikes_count, 0)
        self.assertEqual(reply.get_user_reaction(self.user), "like")

    def test_reply_reaction_htmx_partial_response(self):
        """HTMX POST request to reply reaction receives updated partial buttons template."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="Detailed biblical reply.",
        )
        self.client.force_login(self.user)
        react_url = reverse("discussions:reply_reaction_toggle", kwargs={"pk": reply.id})

        response = self.client.post(react_url, {"vote_type": "like"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "discussions/partials/reply_reaction_buttons.html")
        content = response.content.decode()
        self.assertIn("like-btn", content)
        self.assertIn("active", content)
        self.assertIn(f"reply-reactions-{reply.id}", content)

    def test_reply_reaction_unauthenticated_user_redirected(self):
        """Unauthenticated user POST to reply reaction endpoint is redirected to login."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="Unauthenticated test reply.",
        )
        react_url = reverse("discussions:reply_reaction_toggle", kwargs={"pk": reply.id})
        response = self.client.post(react_url, {"vote_type": "like"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_reply_reaction_deleted_reply_forbidden(self):
        """Cannot react to a deleted reply."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="To be deleted.",
            is_deleted=True,
        )
        self.client.force_login(self.user)
        react_url = reverse("discussions:reply_reaction_toggle", kwargs={"pk": reply.id})

        response = self.client.post(react_url, {"vote_type": "like"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ReplyReaction.objects.count(), 0)

    def test_reply_reaction_invalid_vote_type(self):
        """Invalid vote type on reply returns 400 Bad Request on HTMX."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="Sample reply.",
        )
        self.client.force_login(self.user)
        react_url = reverse("discussions:reply_reaction_toggle", kwargs={"pk": reply.id})

        response = self.client.post(react_url, {"vote_type": "super_vote"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 400)

    def test_reply_reaction_typed_url_pattern(self):
        """User can react to reply using typed URL pattern."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="Testing typed url.",
        )
        self.client.force_login(self.user)
        react_url = reverse("discussions:reply_reaction_toggle_typed", kwargs={"pk": reply.id, "vote_type": "like"})

        response = self.client.post(react_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(reply.likes_count, 1)

    def test_discussion_detail_renders_reply_reaction_buttons(self):
        """Discussion detail template renders reaction buttons on replies."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.responder,
            content="A visible reply with reaction controls.",
        )
        self.client.force_login(self.user)
        response = self.client.get(self.discussion.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"reply-reactions-{reply.id}")
        self.assertContains(response, "reply-reaction-group")

    def test_anonymous_avatar_rendered_on_discussions_and_replies(self):
        """Discussions and replies posted anonymously render the privacy avatar SVG."""
        anon_disc = Discussion.objects.create(
            topic=self.topic,
            author=self.user,
            title="A sensitive anonymous question",
            content="Private content...",
            is_anonymous=True,
        )
        anon_reply = Reply.objects.create(
            discussion=anon_disc,
            author=self.responder,
            content="Anonymous reply advice.",
            is_anonymous=True,
        )
        response = self.client.get(anon_disc.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "anonymous_avatar.svg")
        self.assertContains(response, f"reply-{anon_reply.id}")



