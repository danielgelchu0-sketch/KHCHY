import logging
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import FormView, UpdateView

from .forms import UserLoginForm, UserProfileForm, UserRegistrationForm
from .models import Profile, User

logger = logging.getLogger(__name__)


class RegisterView(FormView):
    """Handles new member registration."""
    template_name = "accounts/register.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("discussions:topic_list")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("discussions:topic_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        logger.info(f"New user registered successfully: {user.email} (ID: {user.id})")
        messages.success(
            self.request,
            f"Welcome to HKHC Community, {user.display_name}! Your account has been created successfully.",
        )
        return super().form_valid(form)


MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes


class LoginView(FormView):
    """Handles member authentication with email and password, protected by rate limiting."""
    template_name = "accounts/login.html"
    form_class = UserLoginForm

    def _get_client_ip(self):
        x_forwarded = self.request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return self.request.META.get("REMOTE_ADDR", "127.0.0.1")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("discussions:topic_list")
        if request.method == "POST":
            client_ip = self._get_client_ip()
            key = f"login_fails_{client_ip}"
            fails = cache.get(key, 0)
            if fails >= MAX_FAILED_LOGIN_ATTEMPTS:
                logger.warning(f"Rate limited login attempt from IP {client_ip}")
                return render(
                    request,
                    self.template_name,
                    {
                        "form": self.get_form(),
                        "rate_limited": True,
                    },
                    status=429,
                )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        client_ip = self._get_client_ip()
        cache.delete(f"login_fails_{client_ip}")
        logger.info(f"Successful login for user: {user.email}")
        messages.info(self.request, f"Welcome back, {user.display_name}!")
        next_url = self.request.GET.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect("discussions:topic_list")

    def form_invalid(self, form):
        client_ip = self._get_client_ip()
        key = f"login_fails_{client_ip}"
        fails = cache.get(key, 0) + 1
        cache.set(key, fails, timeout=LOCKOUT_DURATION)
        logger.warning(f"Failed login attempt ({fails}/{MAX_FAILED_LOGIN_ATTEMPTS}) from IP {client_ip}")
        return super().form_invalid(form)


class LogoutView(View):
    """Logs out authenticated users and redirects to landing page."""
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been logged out successfully.")
        return redirect("core:home")

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been logged out successfully.")
        return redirect("core:home")


@method_decorator(login_required, name="dispatch")
class ProfileEditView(View):
    """Allows members to view and update their own profile."""
    template_name = "accounts/profile_edit.html"

    def get(self, request):
        form = UserProfileForm(instance=request.user.profile, user=request.user)
        return render(request, self.template_name, {"form": form, "user": request.user})

    def post(self, request):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect("accounts:profile_edit")
        return render(request, self.template_name, {"form": form, "user": request.user})


@method_decorator(login_required, name="dispatch")
class PublicProfileView(View):
    """
    Renders public member profile.
    CRITICAL PRIVACY RULE: Never expose user's email address or anonymous activity.
    """
    template_name = "accounts/profile_detail.html"

    def get(self, request, user_id):
        member = get_object_or_404(User, id=user_id, is_active=True)
        # Fetch only identified discussions created by this member
        from apps.discussions.models import Discussion, Reply
        identified_discussions = (
            Discussion.objects.filter(author=member, is_anonymous=False, is_deleted=False)
            .select_related("topic")
            .order_by("-created_at")[:10]
        )
        identified_replies_count = Reply.objects.filter(author=member, is_anonymous=False, is_deleted=False).count()

        return render(
            request,
            self.template_name,
            {
                "member": member,
                "discussions": identified_discussions,
                "replies_count": identified_replies_count,
            },
        )


# Password Reset Views customized with HKHC templates
class CustomPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
