from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.discussions.models import Discussion, Reply, Topic

User = get_user_model()


class PerformanceAndQueryCountTests(TestCase):
    """Test suite ensuring querysets use select_related and prefetch_related without N+1 regression."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="author@example.com", password="Pass123!Password", display_name="Performance Tester"
        )
        self.topic = Topic.objects.create(name="Performance Room", slug="perf-room", description="Perf test room")
        self.discussion = Discussion.objects.create(
            topic=self.topic,
            author=self.user,
            title="Performance Test Question",
            content="Testing query count efficiency...",
        )
        # Create 15 distinct replies with distinct authors
        for i in range(15):
            author_i = User.objects.create_user(
                email=f"perf_user_{i}@example.com", password="Pass123!Password", display_name=f"User {i}"
            )
            Reply.objects.create(
                discussion=self.discussion,
                author=author_i,
                content=f"Reply number {i}",
                is_anonymous=(i % 2 == 0),
            )

    def test_discussion_detail_avoids_n_plus_one_queries(self):
        """
        Rendering discussion detail with 15 replies must execute a low, bounded number
        of database queries rather than issuing 15+ separate queries for authors/profiles.
        """
        self.client.force_login(self.user)
        # Bounded query test: Should execute <= 12 queries total for user, session, topic, discussion, view update, replies tree
        with self.assertNumQueries(11):
            response = self.client.get(self.discussion.get_absolute_url())
            self.assertEqual(response.status_code, 200)

    def test_topic_detail_avoids_n_plus_one_queries(self):
        """
        Rendering topic detail with 10 discussions avoids N+1 queries for authors and reply counts.
        """
        for i in range(10):
            Discussion.objects.create(
                topic=self.topic,
                author=self.user,
                title=f"Thread #{i}",
                content="Thread content",
            )

        self.client.force_login(self.user)
        # Should execute a fixed small number of queries
        with self.assertNumQueries(6):
            response = self.client.get(self.topic.get_absolute_url())
            self.assertEqual(response.status_code, 200)
