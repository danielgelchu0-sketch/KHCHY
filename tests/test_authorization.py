from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from apps.discussions.models import Discussion, Topic

User = get_user_model()


class AuthorizationTests(TestCase):
    """Test RBAC and role enforcement for members, moderators, and administrators."""

    def setUp(self):
        self.member = User.objects.create_user(
            email="member@example.com", password="Password123!", display_name="Regular Member", role=User.Role.MEMBER
        )
        self.moderator = User.objects.create_user(
            email="moderator@example.com", password="Password123!", display_name="Church Moderator", role=User.Role.MODERATOR
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="Password123!", display_name="Pastor Admin"
        )
        self.topic = Topic.objects.create(name="Youth Room", slug="youth-room", description="Youth questions")
        self.discussion = Discussion.objects.create(
            topic=self.topic,
            author=self.member,
            title="Is it okay to feel doubtful?",
            content="Context about doubts...",
            is_anonymous=False,
        )

    def test_member_cannot_access_moderator_dashboard(self):
        """Regular members receive HTTP 403 Forbidden when trying to access moderator hub."""
        self.client.force_login(self.member)
        response = self.client.get(reverse("moderation:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_moderator_can_access_dashboard(self):
        """Moderator can access dashboard successfully."""
        self.client.force_login(self.moderator)
        response = self.client.get(reverse("moderation:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_member_cannot_apply_moderator_actions(self):
        """Regular member cannot lock or hide discussions."""
        self.client.force_login(self.member)
        action_url = reverse("moderation:discussion_moderate", kwargs={"pk": self.discussion.id})
        response = self.client.post(action_url, {"action": "hide"})
        self.assertEqual(response.status_code, 403)
        self.discussion.refresh_from_db()
        self.assertEqual(self.discussion.status, Discussion.Status.ACTIVE)

    def test_moderator_can_lock_and_hide_discussion(self):
        """Moderator can lock and hide discussions."""
        self.client.force_login(self.moderator)
        action_url = reverse("moderation:discussion_moderate", kwargs={"pk": self.discussion.id})
        response = self.client.post(action_url, {"action": "lock", "reason": "Cooling off period."}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.discussion.refresh_from_db()
        self.assertEqual(self.discussion.status, Discussion.Status.LOCKED)

    def test_account_status_middleware_kicks_suspended_user(self):
        """If a logged-in user is suspended, middleware intercepts them and terminates their session."""
        self.client.force_login(self.member)
        # Suspend member
        self.member.status = User.AccountStatus.SUSPENDED
        self.member.suspended_until = timezone.now() + timedelta(days=7)
        self.member.suspension_reason = "Guideline violation."
        self.member.save()

        response = self.client.get(reverse("discussions:topic_list"))
        # Should redirect to login with warning message
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
