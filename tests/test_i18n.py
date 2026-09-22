from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

User = get_user_model()


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

    def test_logo_and_favicons_render_across_pages(self):
        """Test that the application logo and favicons are rendered in layout and auth templates."""
        home_res = self.client.get(reverse("core:home"))
        self.assertEqual(home_res.status_code, 200)
        self.assertContains(home_res, "img/logo.png")
        self.assertContains(home_res, "img/favicon-32x32.png")
        self.assertContains(home_res, "brand-logo-img")

        login_res = self.client.get(reverse("accounts:login"))
        self.assertEqual(login_res.status_code, 200)
        self.assertContains(login_res, "img/logo.png")
        self.assertContains(login_res, "brand-logo-img-lg")

        register_res = self.client.get(reverse("accounts:register"))
        self.assertEqual(register_res.status_code, 200)
        self.assertContains(register_res, "img/logo.png")
        self.assertContains(register_res, "brand-logo-img-lg")

    def test_mobile_navigation_guest_elements_rendered(self):
        """Guest mobile navbar renders toggle button, quick guest subbar, and drawer without side-sliding."""
        res = self.client.get(reverse("core:home"))
        self.assertEqual(res.status_code, 200)
        # Mobile Menu Toggle Button
        self.assertContains(res, "id=\"mobile-menu-toggle\"")
        self.assertContains(res, "icon-hamburger")
        self.assertContains(res, "Menu")
        # Mobile Subbar for Guest
        self.assertContains(res, "mobile-subbar")
        self.assertContains(res, "mobile-guest-welcome")
        self.assertContains(res, "Welcome to HKHC")
        self.assertContains(res, "btn-subbar-login")
        self.assertContains(res, "btn-subbar-join")
        # Mobile Drawer & Backdrop
        self.assertContains(res, "id=\"mobile-drawer\"")
        self.assertContains(res, "id=\"mobile-drawer-backdrop\"")
        self.assertContains(res, "id=\"mobile-drawer-close\"")
        self.assertContains(res, "drawer-search-form")
        self.assertContains(res, "Explore Fellowship")

    def test_mobile_navigation_authenticated_member_elements_rendered(self):
        """Authenticated user sees user badge, direct settings, logout in mobile subbar, and notification bell."""
        user = User.objects.create_user(
            email="churchmember@example.com",
            password="StrongPassword123!",
            display_name="Elder Thomas",
        )
        self.client.force_login(user)
        res = self.client.get(reverse("discussions:topic_list"))
        self.assertEqual(res.status_code, 200)
        # Mobile Subbar with User Name and direct Settings & Logout
        self.assertContains(res, "mobile-subbar")
        self.assertContains(res, "Elder Thomas")
        self.assertContains(res, reverse("accounts:profile_edit"))
        self.assertContains(res, reverse("accounts:logout"))
        # Notification link visible in top bar with HTMX polling badge
        self.assertContains(res, "nav-notification-badge")
        self.assertContains(res, reverse("notifications:list"))
        # Mobile drawer contains member profile overview
        self.assertContains(res, "drawer-user-info")
        self.assertContains(res, "Community Member")

    def test_mobile_navigation_amharic_translations(self):
        """In Amharic mode, mobile menu, subbar, and drawer render proper translated labels."""
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "am"
        res = self.client.get(reverse("core:home"))
        self.assertEqual(res.status_code, 200)
        # Menu translated to ምናሌ
        self.assertContains(res, "ምናሌ")
        # Guest subbar translated
        self.assertContains(res, "እንኳን ወደ HKHC በደህና መጡ")
        self.assertContains(res, "ይግቡ")
        self.assertContains(res, "ማህበረሰቡን ይቀላቀሉ")
        # Drawer sections translated
        self.assertContains(res, "ውይይቶችን ያስሱ")
        self.assertContains(res, "መለያ እና ቅንብሮች")




