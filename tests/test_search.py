from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.discussions.models import Discussion, Topic

User = get_user_model()


class SearchTests(TestCase):
    """Test suite covering search across topics, discussions, content, and privacy enforcement."""

    def setUp(self):
        self.member = User.objects.create_user(
            email="searcher@example.com", password="Pass123!Password", display_name="Search User"
        )
        self.secret_author = User.objects.create_user(
            email="secret_author@example.com", password="Pass123!Password", display_name="Secret Author"
        )

        self.topic1 = Topic.objects.create(
            name="Faith & Spiritual Life", slug="faith-spiritual-life", description="Prayer and spiritual growth."
        )
        self.topic2 = Topic.objects.create(
            name="Youth Questions", slug="youth-questions", description="Youth and teenage challenges."
        )

        self.disc_active = Discussion.objects.create(
            topic=self.topic1,
            author=self.member,
            title="Understanding Grace and Redemption",
            content="A deep exploration of biblical grace.",
            is_anonymous=False,
            status=Discussion.Status.ACTIVE,
        )
        self.disc_anon = Discussion.objects.create(
            topic=self.topic2,
            author=self.secret_author,
            title="Anonymous Inquiry About Forgiveness",
            content="How does grace apply when you feel unworthy of forgiveness?",
            is_anonymous=True,
            status=Discussion.Status.ACTIVE,
        )
        self.disc_hidden = Discussion.objects.create(
            topic=self.topic1,
            author=self.member,
            title="Hidden Inappropriate Content Grace",
            content="Spam or inappropriate text",
            is_anonymous=False,
            status=Discussion.Status.HIDDEN,
        )
        self.disc_deleted = Discussion.objects.create(
            topic=self.topic1,
            author=self.member,
            title="Deleted Discussion Grace",
            content="Old text",
            is_anonymous=False,
            is_deleted=True,
            status=Discussion.Status.ACTIVE,
        )

    def test_search_matches_title_and_content(self):
        """Searching for 'Grace' returns active discussions matching title or content."""
        search_url = reverse("core:search")
        response = self.client.get(search_url, {"q": "Grace"})
        self.assertEqual(response.status_code, 200)

        # Active discussions included
        self.assertContains(response, "Understanding Grace and Redemption")
        self.assertContains(response, "Anonymous Inquiry About Forgiveness")

        # Hidden or soft-deleted discussions must NOT be returned in search
        self.assertNotContains(response, "Hidden Inappropriate Content Grace")
        self.assertNotContains(response, "Deleted Discussion Grace")

    def test_search_matches_topics(self):
        """Searching for 'Youth' returns matching topics."""
        search_url = reverse("core:search")
        response = self.client.get(search_url, {"q": "Youth"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Youth Questions")

    def test_search_preserves_anonymity_in_results(self):
        """Ordinary user viewing search results cannot see anonymous author identity."""
        self.client.force_login(self.member)
        search_url = reverse("core:search")
        response = self.client.get(search_url, {"q": "Forgiveness"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anonymous Member")
        self.assertNotContains(response, self.secret_author.display_name)
        self.assertNotContains(response, self.secret_author.email)

    def test_empty_search_query_handled_gracefully(self):
        """Empty search query returns search page without errors."""
        search_url = reverse("core:search")
        response = self.client.get(search_url, {"q": ""})
        self.assertEqual(response.status_code, 200)
