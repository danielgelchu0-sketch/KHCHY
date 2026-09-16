from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import translation


class InternationalizationTests(TestCase):
    """
    Test suite for bilingual features: English / Amharic language switching,
    cookies, session storage, and natural Amharic rendering.
    """

    def test_default_language_is_english(self):
        """Default platform language should be English."""
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HKHC Community")
        self.assertContains(response, "Eng")
        self.assertContains(response, "አማ (Amh)")

    def test_toggle_language_to_amharic_via_post(self):
        """Switching language to Amharic sets session and cookie."""
        response = self.client.post(
            reverse("core:toggle_language"),
            {"language": "am", "next": reverse("core:home")},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:home"))
        self.assertIn(settings.LANGUAGE_COOKIE_NAME, response.cookies)
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "am")
        self.assertEqual(self.client.session.get("django_language"), "am")

    def test_toggle_language_toggles_back_to_english(self):
        """Switching language back to English from Amharic."""
        # Set to Amharic first
        self.client.post(reverse("core:toggle_language"), {"language": "am"})
        # Now toggle to English
        response = self.client.post(
            reverse("core:toggle_language"),
            {"language": "en", "next": reverse("core:home")},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "en")
        self.assertEqual(self.client.session.get("django_language"), "en")

    def test_toggle_without_language_param_alternates(self):
        """Calling toggle without a language parameter automatically flips language."""
        # Default is en -> should flip to am
        response = self.client.get(reverse("core:toggle_language"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "am")

        # Now in am -> should flip to en
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "am"
        response = self.client.get(reverse("core:toggle_language"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "en")

    def test_toggle_language_unsafe_redirect_prevention(self):
        """Prevent open redirect attacks on language toggle."""
        response = self.client.post(
            reverse("core:toggle_language"),
            {"language": "am", "next": "https://malicious-site.example.com/steal"},
        )
        self.assertEqual(response.status_code, 302)
        # Unsafe redirect should be normalized to "/"
        self.assertEqual(response.url, "/")

    def test_pages_render_in_amharic(self):
        """Pages should render culturally and spiritually natural Amharic text when activated."""
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "am"

        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        # Verify key natural Amharic strings appear on the homepage
        self.assertContains(response, "የውይይት ክፍሎች")  # Discussion Rooms
        self.assertContains(response, "የHKHC ማህበረሰብ")  # HKHC Community
        self.assertContains(response, "የማህበረሰብ ደንቦችና መመሪያዎች")  # Community Guidelines
        self.assertContains(response, "መመሪያዎች")  # Guidelines nav link

    def test_guidelines_and_privacy_render_in_amharic(self):
        """Guidelines and privacy pages render fully in Amharic."""
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "am"

        # Guidelines
        guidelines_res = self.client.get(reverse("core:guidelines"))
        self.assertEqual(guidelines_res.status_code, 200)
        self.assertContains(guidelines_res, "የማህበረሰብ ደንቦችና መመሪያዎች")
        self.assertContains(guidelines_res, "የጸጋ እና የእውነት መንፈስ")

        # Privacy Policy
        privacy_res = self.client.get(reverse("core:privacy_policy"))
        self.assertEqual(privacy_res.status_code, 200)
        self.assertContains(privacy_res, "የግላዊነት፣ የሚስጥራዊነት እና የደህንነት መመሪያ")
        self.assertContains(privacy_res, "ሚስጥራዊነት እንዴት እንደሚሰራ")

    def test_login_and_register_render_in_amharic(self):
        """Auth pages render with proper Amharic labels."""
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "am"

        login_res = self.client.get(reverse("accounts:login"))
        self.assertEqual(login_res.status_code, 200)
        self.assertContains(login_res, "ወደ ቤተክርስቲያን ማህበረሰብ መለያዎ ይግቡ")

        register_res = self.client.get(reverse("accounts:register"))
        self.assertEqual(register_res.status_code, 200)
        self.assertContains(register_res, "ማህበረሰቡን ይቀላቀሉ")
        self.assertContains(register_res, "የማህበረሰብ መገለጫ ስም")

    def test_how_to_use_renders_in_english_and_amharic(self):
        """User guide page renders successfully in English and Amharic with navigation links."""
        # English view
        en_res = self.client.get(reverse("core:how_to_use"))
        self.assertEqual(en_res.status_code, 200)
        self.assertContains(en_res, "How to Use the HKHC Community Platform")
        self.assertContains(en_res, "Choosing Your Identity: With Your Name vs. Anonymous")
        self.assertContains(en_res, "Reacting with Likes & Dislikes (On Posts and Replies)")

        # Amharic view
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "am"
        am_res = self.client.get(reverse("core:how_to_use"))
        self.assertEqual(am_res.status_code, 200)
        self.assertContains(am_res, "የHKHC ማህበረሰብ መድረክ አጠቃቀም መመሪያ")
        self.assertContains(am_res, "ማንነትን መምረጥ፡ በግልጽ ስም ወይስ በሚስጥር")
        self.assertContains(am_res, "Like እና Dislike")

    def test_navbar_and_footer_contain_user_guide_links(self):
        """Base layout navbar and footer include user guide links."""
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("core:how_to_use"))

    def test_homepage_renders_community_hero_banner(self):
        """Home page displays the non-distracting community hero banner artwork."""
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "community-hero-banner")
        self.assertContains(response, "community_banner_art.svg")

    def test_topic_list_renders_welcome_banner_and_avatar(self):
        """Topic list page displays the community avatar emblem welcome banner."""
        response = self.client.get(reverse("discussions:topic_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "topic-welcome-banner")
        self.assertContains(response, "community_avatar.svg")


