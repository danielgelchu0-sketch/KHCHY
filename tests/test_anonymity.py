from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.discussions.models import Discussion, Reply, Topic

User = get_user_model()


class AnonymityModelTests(TestCase):
    """
    Test suite verifying strict anonymity enforcement:
    - Zero identity leaks (name, email, user ID, avatar) for ordinary members.
    - True authenticated author preserved in database.
    - Authorized pastoral moderators can inspect author identity for safety.
    - Tampering with request cannot bypass validation.
    """

    def setUp(self):
        self.ordinary_user = User.objects.create_user(
            email="ordinary@example.com", password="Pass123!Password", display_name="John Doe"
        )
        self.author_user = User.objects.create_user(
            email="sensitive_youth@example.com", password="Pass123!Password", display_name="Vulnerable Teen"
        )
        self.moderator = User.objects.create_user(
            email="pastor_mod@hkhc.org", password="Pass123!Password", display_name="Pastor Tim", role=User.Role.MODERATOR
        )
        self.topic = Topic.objects.create(name="Youth Room", slug="youth-room", description="Safe space")

        # Anonymous Question
        self.anon_disc = Discussion.objects.create(
            topic=self.topic,
            author=self.author_user,
            title="A sensitive anonymous question about temptation",
            content="I need anonymous guidance on this personal matter.",
            is_anonymous=True,
        )

        # Identified Question
        self.identified_disc = Discussion.objects.create(
            topic=self.topic,
            author=self.author_user,
            title="A public question with my identity",
            content="I am happy to ask this publicly under my real name.",
            is_anonymous=False,
        )

        # Anonymous Reply
        self.anon_reply = Reply.objects.create(
            discussion=self.identified_disc,
            author=self.author_user,
            content="This is an anonymous reply sharing an intimate struggle.",
            is_anonymous=True,
        )

    def test_ordinary_member_sees_no_author_identity_on_anonymous_post(self):
        """Ordinary member viewing an anonymous post sees 'Anonymous Member' and zero author leaks."""
        self.client.force_login(self.ordinary_user)
        response = self.client.get(self.anon_disc.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anonymous Member")
        # STRICT PRIVACY: Author's display name, email, or user ID must NEVER appear in HTML
        self.assertNotContains(response, self.author_user.display_name)
        self.assertNotContains(response, self.author_user.email)
        self.assertNotContains(response, f"/member/{self.author_user.id}/")

    def test_anonymous_reply_hides_identity_from_ordinary_members(self):
        """Ordinary member viewing a discussion with an anonymous reply cannot see reply author."""
        self.client.force_login(self.ordinary_user)
        response = self.client.get(self.identified_disc.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        # Main identified question shows display name
        self.assertContains(response, self.author_user.display_name)
        # But the anonymous reply has Anonymous Member
        self.assertContains(response, "Anonymous Member")
        # Ensure reply author link is not rendered for the anonymous reply
        self.assertNotContains(response, f"public_profile/{self.author_user.id}")

    def test_database_preserves_true_author_for_anonymous_posts(self):
        """Database never stores dummy/fake authors; true authenticated user is preserved."""
        self.assertEqual(self.anon_disc.author_id, self.author_user.id)
        self.assertTrue(self.anon_disc.is_anonymous)
        self.assertEqual(self.anon_reply.author_id, self.author_user.id)
        self.assertTrue(self.anon_reply.is_anonymous)

    def test_moderator_can_inspect_anonymous_author(self):
        """Authorized moderators viewing the discussion can see the internal author inspection banner."""
        self.client.force_login(self.moderator)
        response = self.client.get(self.anon_disc.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Moderator Author Inspection")
        self.assertContains(response, self.author_user.display_name)
        self.assertContains(response, self.author_user.email)

    def test_anonymity_mode_selection_on_discussion_creation(self):
        """Posting anonymously sets is_anonymous=True; posting identified sets is_anonymous=False."""
        self.client.force_login(self.author_user)
        url = reverse("discussions:discussion_create", kwargs={"topic_slug": self.topic.slug})

        # Post 1: Anonymous
        res1 = self.client.post(url, {
            "title": "New Anonymous Struggle",
            "content": "Detailed context for this question...",
            "post_mode": "anonymous",
        }, follow=True)
        self.assertEqual(res1.status_code, 200)
        new_anon = Discussion.objects.get(title="New Anonymous Struggle")
        self.assertTrue(new_anon.is_anonymous)

        # Post 2: Identified
        res2 = self.client.post(url, {
            "title": "New Identified Discussion",
            "content": "Detailed context for this question...",
            "post_mode": "identified",
        }, follow=True)
        self.assertEqual(res2.status_code, 200)
        new_ident = Discussion.objects.get(title="New Identified Discussion")
        self.assertFalse(new_ident.is_anonymous)

    def test_tampering_post_mode_rejected(self):
        """Submitting an invalid post_mode value is caught and rejected by server validation."""
        self.client.force_login(self.author_user)
        url = reverse("discussions:discussion_create", kwargs={"topic_slug": self.topic.slug})

        res = self.client.post(url, {
            "title": "Tampered Mode Attempt",
            "content": "Detailed context...",
            "post_mode": "bypass_anonymity_hack",
        })
        self.assertFormError(res.context["form"], "post_mode", "You must select a valid posting identity mode.")
