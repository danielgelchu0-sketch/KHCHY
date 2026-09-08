from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AuthenticationTests(TestCase):
    """Test suite covering member registration, login, logout, and password resets."""

    def setUp(self):
        self.register_url = reverse("accounts:register")
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")
        self.password_reset_url = reverse("accounts:password_reset")

        self.user_data = {
            "email": "tester@example.com",
            "display_name": "Tester Person",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "agree_to_guidelines": True,
        }

    def test_successful_registration(self):
        """User registers successfully with valid email, display name, and password."""
        response = self.client.post(self.register_url, self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)

        user = User.objects.filter(email="tester@example.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.display_name, "Tester Person")
        self.assertEqual(user.role, User.Role.MEMBER)
        self.assertEqual(user.status, User.AccountStatus.ACTIVE)
        self.assertTrue(user.check_password("SecurePassword123!"))
        # Verify profile creation signal
        self.assertTrue(hasattr(user, "profile"))
        # Verify user is authenticated in session
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_registration_duplicate_email_rejected(self):
        """Registration fails when email already exists."""
        User.objects.create_user(email="tester@example.com", password="Pass123!Password", display_name="Existing")
        response = self.client.post(self.register_url, self.user_data)
        self.assertFormError(response.context["form"], "email", "An account with this email address already exists.")

    def test_registration_password_mismatch(self):
        """Registration fails when confirm password does not match."""
        data = self.user_data.copy()
        data["confirm_password"] = "DifferentPassword999!"
        response = self.client.post(self.register_url, data)
        self.assertFormError(response.context["form"], "confirm_password", "Passwords do not match.")

    def test_registration_reserved_display_names(self):
        """Display names containing 'admin', 'moderator', 'anonymous' are rejected."""
        data = self.user_data.copy()
        data["display_name"] = "Church Admin"
        response = self.client.post(self.register_url, data)
        self.assertFormError(response.context["form"], "display_name", "Display name cannot contain reserved words (admin, moderator, anonymous).")

    def test_successful_login_and_logout(self):
        """Member can log in with email and password, and log out cleanly."""
        user = User.objects.create_user(email="loginuser@example.com", password="ValidPassword123!", display_name="Login User")
        response = self.client.post(self.login_url, {
            "email": "loginuser@example.com",
            "password": "ValidPassword123!",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

        # Logout
        logout_response = self.client.post(self.logout_url, follow=True)
        self.assertEqual(logout_response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_invalid_password(self):
        """Login fails with invalid password."""
        User.objects.create_user(email="loginuser@example.com", password="ValidPassword123!")
        response = self.client.post(self.login_url, {
            "email": "loginuser@example.com",
            "password": "WrongPassword999!",
        })
        self.assertContains(response, "Invalid email address or password.")

    def test_banned_user_cannot_login(self):
        """Banned users cannot authenticate."""
        user = User.objects.create_user(email="banned@example.com", password="ValidPassword123!")
        user.status = User.AccountStatus.BANNED
        user.save()

        response = self.client.post(self.login_url, {
            "email": "banned@example.com",
            "password": "ValidPassword123!",
        })
        self.assertContains(response, "This account has been deactivated or banned.")

    def test_password_reset_flow(self):
        """Password reset email is sent and password can be updated."""
        user = User.objects.create_user(email="resetme@example.com", password="OldPassword123!")
        response = self.client.post(self.password_reset_url, {"email": "resetme@example.com"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Password Reset Request", mail.outbox[0].subject)
        self.assertIn("resetme@example.com", mail.outbox[0].to)

    def test_login_rate_limiting_after_repeated_failures(self):
        """Repeated failed login attempts trigger rate limiting (HTTP 429)."""
        from django.core.cache import cache
        cache.clear()
        User.objects.create_user(email="victim@example.com", password="CorrectPassword123!")

        # 5 failed attempts
        for _ in range(5):
            self.client.post(self.login_url, {
                "email": "victim@example.com",
                "password": "WrongPassword999!",
            })

        # 6th attempt should return HTTP 429
        response = self.client.post(self.login_url, {
            "email": "victim@example.com",
            "password": "WrongPassword999!",
        })
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many failed login attempts", status_code=429)
        cache.clear()
