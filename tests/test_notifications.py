from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.discussions.models import Bookmark, Discussion, Reply, Topic
from apps.notifications.models import Notification
from apps.notifications.services import create_reply_notifications

User = get_user_model()


class NotificationTests(TestCase):
    """Test suite covering notifications for questions, comments, bookmarks, and privacy rules."""

    def setUp(self):
        self.question_author = User.objects.create_user(
            email="author@example.com", password="Pass123!Password", display_name="Question Author"
        )
        self.commenter = User.objects.create_user(
            email="commenter@example.com", password="Pass123!Password", display_name="First Commenter"
        )
        self.replier = User.objects.create_user(
            email="replier@example.com", password="Pass123!Password", display_name="Helpful Replier"
        )
        self.follower = User.objects.create_user(
            email="follower@example.com", password="Pass123!Password", display_name="Interested Follower"
        )
        self.topic = Topic.objects.create(name="Youth Room", slug="youth-room", description="Youth")

        self.discussion = Discussion.objects.create(
            topic=self.topic,
            author=self.question_author,
            title="Guidance on Prayer",
            content="How do you sustain a faithful prayer habit?",
            is_anonymous=False,
        )

        Bookmark.objects.create(user=self.follower, discussion=self.discussion)

    def test_reply_dispatches_notification_to_question_author_and_follower(self):
        """Posting a reply notifies both the discussion author and discussion followers."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.replier,
            content="Setting a designated quiet time early in the morning helped me greatly.",
            is_anonymous=False,
        )
        create_reply_notifications(reply)

        # Question author should receive notification
        notif_author = Notification.objects.filter(recipient=self.question_author).first()
        self.assertIsNotNone(notif_author)
        self.assertEqual(notif_author.notification_type, Notification.NotificationType.REPLY_QUESTION)
        self.assertIn("Helpful Replier", notif_author.message)

        # Follower should receive bookmark update notification
        notif_follower = Notification.objects.filter(recipient=self.follower).first()
        self.assertIsNotNone(notif_follower)
        self.assertEqual(notif_follower.notification_type, Notification.NotificationType.BOOKMARK_UPDATE)

    def test_anonymous_reply_does_not_leak_identity_in_notification(self):
        """When an anonymous reply is created, notification message uses neutral community label."""
        reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.replier,
            content="I also struggle with consistency, you are not alone.",
            is_anonymous=True,
        )
        create_reply_notifications(reply)

        notif = Notification.objects.filter(recipient=self.question_author).first()
        self.assertIsNotNone(notif)
        self.assertNotIn(self.replier.display_name, notif.message)
        self.assertNotIn(self.replier.email, notif.message)
        self.assertIn("A community member", notif.message)

    def test_nested_reply_notifies_parent_comment_author(self):
        """Nested replies notify the parent reply's author."""
        parent_reply = Reply.objects.create(
            discussion=self.discussion,
            author=self.commenter,
            content="I read Psalm 23 every morning.",
            is_anonymous=False,
        )
        nested_reply = Reply.objects.create(
            discussion=self.discussion,
            parent=parent_reply,
            author=self.replier,
            content="That psalm brings great comfort.",
            is_anonymous=False,
        )
        create_reply_notifications(nested_reply)

        notif = Notification.objects.filter(recipient=self.commenter).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.notification_type, Notification.NotificationType.REPLY_COMMENT)

    def test_mark_notification_as_read(self):
        """User can mark a single notification as read."""
        notif = Notification.objects.create(
            recipient=self.question_author,
            notification_type=Notification.NotificationType.MODERATION,
            title="Welcome",
            message="Welcome to HKHC Community",
            link="/",
        )
        self.client.force_login(self.question_author)
        url = reverse("notifications:mark_read", kwargs={"pk": notif.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_user_cannot_mark_another_users_notification(self):
        """User B cannot mark User A's notification as read."""
        notif = Notification.objects.create(
            recipient=self.question_author,
            notification_type=Notification.NotificationType.MODERATION,
            title="Private",
            message="Private alert",
            link="/",
        )
        self.client.force_login(self.replier)
        url = reverse("notifications:mark_read", kwargs={"pk": notif.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        notif.refresh_from_db()
        self.assertFalse(notif.is_read)

    def test_mark_all_notifications_read(self):
        """User can mark all unread notifications as read at once."""
        for i in range(3):
            Notification.objects.create(
                recipient=self.question_author,
                notification_type=Notification.NotificationType.MODERATION,
                title=f"Alert {i}",
                message="Message",
                link="/",
            )
        self.client.force_login(self.question_author)
        url = reverse("notifications:mark_all_read")
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Notification.objects.filter(recipient=self.question_author, is_read=False).count(), 0)
