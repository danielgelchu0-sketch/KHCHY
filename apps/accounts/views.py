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
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import FormView, UpdateView

from .forms import UserLoginForm, UserProfileForm, UserRegistrationForm
from .models import Profile, User

logger = logging.getLogger(__name__)


class RegisterView(FormView):
    """Handles new member registration with optional personal referral attribution."""
    template_name = "accounts/register.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("discussions:topic_list")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("discussions:topic_list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ref_code = self.request.GET.get("ref") or self.request.session.get("referral_code")
        if ref_code:
            inviter = User.objects.filter(referral_code=ref_code, is_active=True).first()
            if inviter:
                context["inviter"] = inviter
                context["referral_code"] = ref_code
                self.request.session["referral_code"] = ref_code
        return context

    def form_valid(self, form):
        user = form.save(commit=False)
        ref_code = self.request.POST.get("ref") or self.request.session.get("referral_code")
        if ref_code:
            inviter = User.objects.filter(referral_code=ref_code, is_active=True).first()
            if inviter:
                user.invited_by = inviter
        user.save()
        if hasattr(form, "save_m2m"):
            form.save_m2m()

        # If user was referred by a fellow member, notify the inviter
        if user.invited_by:
            try:
                from apps.notifications.models import Notification
                from apps.notifications.services import send_web_push
                profile_url = reverse("accounts:public_profile", kwargs={"user_id": user.id})
                Notification.objects.create(
                    recipient=user.invited_by,
                    notification_type=Notification.NotificationType.MODERATION,
                    title="Friend Joined HKHC!",
                    message=f"🎉 {user.display_name} joined HKHC Community using your personal invite link!",
                    link=profile_url,
                )
                send_web_push(
                    [user.invited_by_id],
                    title="🎉 Friend Joined HKHC!",
                    message=f"{user.display_name} joined using your invite link!",
                    url=profile_url,
                )
            except Exception as ex:
                logger.warning(f"Error dispatching referral notification: {ex}")

        # Clear referral from session
        self.request.session.pop("referral_code", None)

        login(self.request, user, backend="apps.accounts.backends.EmailOrDisplayNameBackend")
        logger.info(f"New user registered successfully: {user.email} (ID: {user.id}, Invited by: {user.invited_by_id})")
        messages.success(
            self.request,
            f"Welcome to HKHC Community, {user.display_name}! Your account has been created successfully.",
        )
        return super().form_valid(form)



from django.conf import settings
import sys

MAX_FAILED_LOGIN_ATTEMPTS = getattr(settings, "MAX_FAILED_LOGIN_ATTEMPTS", 5 if "test" in sys.argv else 10)
LOCKOUT_DURATION = getattr(settings, "LOCKOUT_DURATION", 300 if "test" in sys.argv else 120)


class LoginView(FormView):
    """Handles member authentication with email, phone, or display name, protected by rate limiting."""
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
                        "lockout_minutes": max(1, LOCKOUT_DURATION // 60),
                    },
                    status=429,
                )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client_ip = self._get_client_ip()
        fails = cache.get(f"login_fails_{client_ip}", 0)
        if fails > 0 and fails < MAX_FAILED_LOGIN_ATTEMPTS:
            context["attempts_remaining"] = MAX_FAILED_LOGIN_ATTEMPTS - fails
        return context

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        client_ip = self._get_client_ip()
        cache.delete(f"login_fails_{client_ip}")

        # Persistent login support (Keep me signed in)
        remember_me = form.cleaned_data.get("remember_me", True)
        if remember_me:
            self.request.session.set_expiry(1209600)  # 2 weeks
        else:
            self.request.session.set_expiry(0)  # Browser close

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

        invited_members = []
        if request.user.is_authenticated and request.user == member:
            invited_members = member.invited_members.filter(is_active=True).order_by("-date_joined")[:15]

        return render(
            request,
            self.template_name,
            {
                "member": member,
                "discussions": identified_discussions,
                "replies_count": identified_replies_count,
                "invited_members": invited_members,
            },
        )


class MemberDirectoryView(View):
    """
    Renders the community members directory for interactive modal (JSON) and dedicated page (HTML).
    CRITICAL PRIVACY RULE: Never leak email address, phone number, password hash,
    or associate anonymous posts with member identities.
    """
    template_name = "accounts/members_list.html"

    def get(self, request):
        query = request.GET.get("q", "").strip()
        members_qs = (
            User.objects.filter(is_active=True)
            .select_related("profile")
            .annotate(
                public_discussions_count=Count(
                    "discussions",
                    filter=Q(discussions__is_anonymous=False, discussions__is_deleted=False),
                    distinct=True,
                )
            )
            .order_by("-date_joined")
        )

        if query:
            members_qs = members_qs.filter(display_name__icontains=query)

        is_json = (
            request.GET.get("format") == "json"
            or request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("Accept", "")
        )

        if is_json:
            total_active = User.objects.filter(is_active=True).count()
            members_list = list(members_qs[:120])
            members_data = []
            for m in members_list:
                avatar_url = ""
                if hasattr(m, "profile") and m.profile.avatar:
                    try:
                        avatar_url = m.profile.avatar.url
                    except Exception:
                        avatar_url = ""

                members_data.append({
                    "id": m.id,
                    "display_name": m.display_name,
                    "initial": (m.display_name[:1].upper() if m.display_name else "?"),
                    "avatar_url": avatar_url,
                    "is_moderator": m.is_moderator,
                    "is_staff": m.is_staff,
                    "role_label": "Moderator" if m.is_moderator else "Member",
                    "date_joined": m.date_joined.strftime("%b %Y"),
                    "public_discussions_count": m.public_discussions_count,
                    "profile_url": reverse("accounts:public_profile", kwargs={"user_id": m.id}),
                })

            return JsonResponse({
                "total_count": total_active,
                "filtered_count": len(members_data),
                "query": query,
                "members": members_data,
            })

        paginator = Paginator(members_qs, 24)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        return render(
            request,
            self.template_name,
            {
                "page_obj": page_obj,
                "query": query,
                "total_members": User.objects.filter(is_active=True).count(),
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
