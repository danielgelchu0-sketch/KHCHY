import json
from django.test import TestCase
from django.urls import reverse


class PWATests(TestCase):
    """Test suite for Progressive Web App (PWA) manifest, service worker, and offline fallback."""

    def test_root_manifest_endpoint(self):
        """Root /manifest.json returns valid JSON with correct PWA fields."""
        response = self.client.get("/manifest.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["display"], "standalone")
        self.assertEqual(data["start_url"], "/")
        self.assertIn("icons", data)
        self.assertGreaterEqual(len(data["icons"]), 2)

    def test_core_manifest_named_route(self):
        """Core manifest route returns 200."""
        url = reverse("core:manifest")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_offline_page_endpoint(self):
        """Offline fallback page returns 200 with appropriate bilingual notice."""
        url = reverse("core:offline")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Offline")
        self.assertContains(response, "መስመር ላይ አይደሉም")

    def test_service_worker_endpoint(self):
        """Root /sw.js serves valid service worker with caching and Service-Worker-Allowed header."""
        response = self.client.get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/javascript")
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        content = response.content.decode("utf-8")
        self.assertIn("hkhc-static-v2", content)
        self.assertIn("hkhc-pages-v2", content)
        self.assertIn("offline", content)

    def test_base_template_has_pwa_meta_tags(self):
        """Base template renders manifest link, theme color, and install elements."""
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'rel="manifest"')
        self.assertContains(response, 'name="theme-color"')
        self.assertContains(response, 'id="nav-install-btn"')
        self.assertContains(response, 'id="offline-indicator"')
