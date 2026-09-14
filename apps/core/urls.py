from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("privacy-policy/", views.PrivacyPolicyView.as_view(), name="privacy_policy"),
    path("guidelines/", views.CommunityGuidelinesView.as_view(), name="guidelines"),
    path("language/toggle/", views.toggle_language, name="toggle_language"),
]
