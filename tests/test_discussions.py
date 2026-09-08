from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.discussions.models import Bookmark, Discussion, Reply, Topic

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
