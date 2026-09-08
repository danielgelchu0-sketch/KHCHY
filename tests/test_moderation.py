from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.discussions.models import Discussion, Reply, Topic
from apps.moderation.models import AuditLog, Report
from apps.notifications.models import Notification

User = get_user_model()


class ModerationTests(TestCase):
    """Test suite covering reporting, moderator reviews, content actions, user sanctions, and audit logging."""

    def setUp(self):
        self.member = User.objects.create_user(
            email="reporting_member@example.com", password="Pass123!Password", display_name="Vigilant Member"
        )
        self.violator = User.objects.create_user(
            email="violator@example.com", password="Pass123!Password", display_name="Spam User"
        )
        self.moderator = User.objects.create_user(
            email="mod@hkhc.org", password="Pass123!Password", display_name="Pastor Mod", role=User.Role.MODERATOR
        )
        self.topic = Topic.objects.create(name="General", slug="general", description="General discussion")
        self.discussion = Discussion.objects.create(
            topic=self.topic,
            author=self.violator,
            title="Spam question selling crypto",
            content="Buy crypto now at spam site!",
            is_anonymous=False,
        )

    def test_member_can_report_discussion(self):
        """Member can submit a report with a category and description."""
        self.client.force_login(self.member)
        report_url = reverse("moderation:report_submit")
        response = self.client.post(report_url, {
            "type": "discussion",
            "id": self.discussion.id,
            "category": Report.Category.SPAM,
            "description": "This is commercial advertising spam.",
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        report = Report.objects.filter(target_discussion=self.discussion).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reporter, self.member)
        self.assertEqual(report.category, Report.Category.SPAM)
        self.assertEqual(report.status, Report.Status.PENDING)

    def test_duplicate_report_prevention(self):
        """A user cannot submit multiple active reports on the same item."""
        self.client.force_login(self.member)
        report_url = reverse("moderation:report_submit")
        # Submit first report
        self.client.post(report_url, {
            "type": "discussion",
            "id": self.discussion.id,
            "category": Report.Category.SPAM,
            "description": "Report 1",
        })
        # Attempt second duplicate report
        self.client.post(report_url, {
            "type": "discussion",
            "id": self.discussion.id,
            "category": Report.Category.SPAM,
            "description": "Report 2 duplicate",
        })
        self.assertEqual(Report.objects.filter(reporter=self.member, target_discussion=self.discussion).count(), 1)

    def test_moderator_can_resolve_report_and_generate_audit_log(self):
        """Moderator reviewing a report can resolve it with an audit note."""
        report = Report.objects.create(
            reporter=self.member,
            target_discussion=self.discussion,
            category=Report.Category.SPAM,
            description="Spam post",
        )
        self.client.force_login(self.moderator)
        review_url = reverse("moderation:report_detail", kwargs={"pk": report.id})

        response = self.client.post(review_url, {
            "action": "resolve",
            "resolution_note": "Spam confirmed. Content hidden and user warned.",
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.RESOLVED)
        self.assertEqual(report.reviewed_by, self.moderator)

        # Verify audit log creation
        audit = AuditLog.objects.filter(action=AuditLog.ActionType.RESOLVE_REPORT).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.moderator, self.moderator)
        self.assertIn("Spam confirmed", audit.reason)

    def test_moderator_can_warn_user(self):
        """Moderator can issue a warning to a user, creating an audit log and notification."""
        self.client.force_login(self.moderator)
        sanction_url = reverse("moderation:user_sanction", kwargs={"user_id": self.violator.id})
        response = self.client.post(sanction_url, {
            "action": "warn",
            "reason": "Repeated inappropriate language in comments.",
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        # Audit log created
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ActionType.WARN_USER, target_user=self.violator).exists())
        # Notification created for violator
        self.assertTrue(Notification.objects.filter(recipient=self.violator, notification_type=Notification.NotificationType.MODERATION).exists())

    def test_moderator_can_suspend_and_ban_user(self):
        """Moderator can suspend and permanently ban an abusive user."""
        self.client.force_login(self.moderator)
        sanction_url = reverse("moderation:user_sanction", kwargs={"user_id": self.violator.id})

        # Suspend 7 days
        self.client.post(sanction_url, {
            "action": "suspend_7",
            "reason": "Harassment of members.",
        }, follow=True)
        self.violator.refresh_from_db()
        self.assertEqual(self.violator.status, User.AccountStatus.SUSPENDED)
        self.assertIsNotNone(self.violator.suspended_until)

        # Permanent Ban
        self.client.post(sanction_url, {
            "action": "ban",
            "reason": "Severe misconduct.",
        }, follow=True)
        self.violator.refresh_from_db()
        self.assertEqual(self.violator.status, User.AccountStatus.BANNED)

    def test_audit_log_list_accessible_only_by_moderators(self):
        """Audit log list view is accessible by moderators and blocked for members."""
        self.client.force_login(self.member)
        res_member = self.client.get(reverse("moderation:audit_log_list"))
        self.assertEqual(res_member.status_code, 403)

        self.client.force_login(self.moderator)
        res_mod = self.client.get(reverse("moderation:audit_log_list"))
        self.assertEqual(res_mod.status_code, 200)
