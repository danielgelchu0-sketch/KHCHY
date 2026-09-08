from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileEditView.as_view(), name="profile_edit"),
    path("member/<int:user_id>/", views.PublicProfileView.as_view(), name="public_profile"),

    # Password Reset URLs
    path("password-reset/", views.CustomPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", views.CustomPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password-reset/confirm/<uidb64>/<token>/", views.CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset/complete/", views.CustomPasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
