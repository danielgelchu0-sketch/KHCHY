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

    def test_login_with_display_name(self):
        """Members can log in using their display name instead of email address."""
        user = User.objects.create_user(
            email="member1@example.com",
            password="MemberPassword123!",
            display_name="ChurchLeader",
        )
        response = self.client.post(self.login_url, {
            "email": "ChurchLeader",
            "password": "MemberPassword123!",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_login_with_case_insensitive_email(self):
        """Members can log in regardless of email casing."""
        user = User.objects.create_user(
            email="member_case@example.com",
            password="CasePassword123!",
            display_name="CaseMember",
        )
        response = self.client.post(self.login_url, {
            "email": "MEMBER_CASE@EXAMPLE.COM",
            "password": "CasePassword123!",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_login_with_typo_tolerance(self):
        """Account created with typo daneildg62 can be logged in with danieldg62 and vice versa."""
        user = User.objects.create_user(
            email="daneildg62@gmail.com",
            password="DanielPassword123!",
            display_name="Daniel",
        )
        response = self.client.post(self.login_url, {
            "email": "danieldg62@gmail.com",
            "password": "DanielPassword123!",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_profile_edit_can_update_email(self):
        """Members can update their private email address in profile settings."""
        user = User.objects.create_user(
            email="initial_email@example.com",
            password="SecurePass123!",
            display_name="OldName",
        )
        self.client.force_login(user)
        profile_url = reverse("accounts:profile_edit")

        response = self.client.post(profile_url, {
            "display_name": "NewName",
            "email": "updated_email@example.com",
            "bio": "Updated bio text.",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.email, "updated_email@example.com")
        self.assertEqual(user.display_name, "NewName")

    def test_profile_edit_rejects_duplicate_email(self):
        """Members cannot update email to one already registered by another user."""
        User.objects.create_user(email="other_user@example.com", password="Password123!", display_name="Other")
        user = User.objects.create_user(email="my_user@example.com", password="Password123!", display_name="Mine")
        self.client.force_login(user)
        profile_url = reverse("accounts:profile_edit")

        response = self.client.post(profile_url, {
            "display_name": "Mine",
            "email": "other_user@example.com",
        })
        self.assertFormError(response.context["form"], "email", "An account with this email address already exists.")
        user.refresh_from_db()
        self.assertEqual(user.email, "my_user@example.com")
