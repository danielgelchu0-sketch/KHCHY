from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from apps.core.utils import sanitize_user_input
from apps.discussions.models import Discussion, Reply, Topic

User = get_user_model()


class SecurityHardeningTests(TestCase):
    """Test suite verifying protection against XSS, IDOR, privilege escalation, and CSRF."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            email="user_a@example.com", password="Pass123!Password", display_name="User A"
        )
        self.user_b = User.objects.create_user(
            email="user_b@example.com", password="Pass123!Password", display_name="User B"
        )
        self.topic = Topic.objects.create(name="Youth Room", slug="youth-room", description="Youth")
        self.discussion_a = Discussion.objects.create(
            topic=self.topic,
            author=self.user_a,
            title="User A's Question",
            content="Original content by User A",
        )

    def test_xss_script_tags_stripped_or_escaped(self):
        """Malicious <script> tags and onerror handlers are completely sanitized."""
        malicious_input = "<script>alert('XSS')</script><img src='x' onerror='alert(1)'><b>Safe Bold</b>"
        clean_output = sanitize_user_input(malicious_input)

        self.assertNotIn("<script>", clean_output)
        self.assertNotIn("alert('XSS')", clean_output)
        self.assertNotIn("onerror", clean_output)
        self.assertIn("<b>Safe Bold</b>", clean_output)

    def test_malicious_javascript_links_sanitized(self):
        """javascript: links are sanitized away."""
        malicious_link = '<a href="javascript:alert(1)">Click me</a>'
        clean_output = sanitize_user_input(malicious_link)
        self.assertNotIn("javascript:", clean_output)

    def test_links_automatically_receive_nofollow_and_noopener(self):
        """Valid external links receive rel='nofollow noopener noreferrer' and target='_blank'."""
        link_input = '<a href="https://example.com">Visit</a>'
        clean_output = sanitize_user_input(link_input)
        self.assertIn('rel="nofollow noopener noreferrer"', clean_output)
        self.assertIn('target="_blank"', clean_output)

    def test_idor_user_cannot_edit_another_users_discussion(self):
        """User B cannot edit User A's discussion via direct object reference (IDOR)."""
        self.client.force_login(self.user_b)
        edit_url = reverse("discussions:discussion_edit", kwargs={"topic_slug": self.topic.slug, "pk": self.discussion_a.id})
        response = self.client.post(edit_url, {
            "title": "Hacked Title by User B",
            "content": "Malicious override",
            "post_mode": "identified",
        })
        # Should be forbidden
        self.assertEqual(response.status_code, 403)
        self.discussion_a.refresh_from_db()
        self.assertEqual(self.discussion_a.title, "User A's Question")

    def test_idor_user_cannot_delete_another_users_discussion(self):
        """User B cannot delete User A's discussion."""
        self.client.force_login(self.user_b)
        delete_url = reverse("discussions:discussion_delete", kwargs={"topic_slug": self.topic.slug, "pk": self.discussion_a.id})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 403)
        self.discussion_a.refresh_from_db()
        self.assertFalse(self.discussion_a.is_deleted)

    def test_privilege_escalation_attempt_ignored(self):
        """Submitting role='administrator' during registration or profile edit does not elevate role."""
        register_url = reverse("accounts:register")
        self.client.post(register_url, {
            "email": "attacker@example.com",
            "display_name": "Attacker",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "administrator",
            "is_staff": True,
            "is_superuser": True,
            "agree_to_guidelines": True,
        })
        user = User.objects.get(email="attacker@example.com")
        self.assertEqual(user.role, User.Role.MEMBER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_csrf_protection_enforced_for_unauthenticated_client(self):
        """POST request without CSRF token fails with HTTP 403."""
        client = Client(enforce_csrf_checks=True)
        login_url = reverse("accounts:login")
        response = client.post(login_url, {"email": "test@example.com", "password": "pass"})
        self.assertEqual(response.status_code, 403)

    def test_avatar_upload_rejects_oversized_file(self):
        """Profile photo larger than 2MB is rejected by validation."""
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.accounts.forms import UserProfileForm

        img_io = BytesIO()
        Image.new("RGB", (50, 50), color="blue").save(img_io, format="JPEG")
        valid_img_bytes = img_io.getvalue()

        big_file = SimpleUploadedFile("avatar.jpg", valid_img_bytes, content_type="image/jpeg")
        big_file.size = 2 * 1024 * 1024 + 500

        form = UserProfileForm(data={"display_name": "Test User"}, files={"avatar": big_file}, user=self.user_a)
        self.assertFalse(form.is_valid())
        self.assertIn("avatar", form.errors)
        self.assertIn("smaller than 2MB", form.errors["avatar"][0])

    def test_avatar_upload_rejects_disallowed_extension(self):
        """Executable or non-image extensions are rejected."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.accounts.forms import UserProfileForm
        bad_file = SimpleUploadedFile("malicious.exe", b"fake binary", content_type="application/x-msdownload")
        form = UserProfileForm(data={"display_name": "Test User"}, files={"avatar": bad_file}, user=self.user_a)
        self.assertFalse(form.is_valid())
        self.assertIn("avatar", form.errors)
