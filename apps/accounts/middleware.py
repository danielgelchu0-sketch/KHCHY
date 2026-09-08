from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone


class AccountStatusMiddleware:
    """
    Middleware that checks whether an authenticated user is currently suspended or banned.
    If suspended or banned, the user is immediately logged out and notified.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user = request.user
            if user.status == user.AccountStatus.BANNED:
                logout(request)
                messages.error(
                    request,
                    "Your account has been banned due to a community guideline violation. Please contact administration if you believe this is an error.",
                )
                return redirect(reverse("accounts:login"))

            elif user.status == user.AccountStatus.SUSPENDED:
                if user.suspended_until and timezone.now() > user.suspended_until:
                    # Suspension expired, automatically restore active status
                    user.status = user.AccountStatus.ACTIVE
                    user.suspension_reason = ""
                    user.suspended_until = None
                    user.save(update_fields=["status", "suspension_reason", "suspended_until"])
                else:
                    reason = f" Reason: {user.suspension_reason}" if user.suspension_reason else ""
                    until_str = f" until {user.suspended_until.strftime('%Y-%m-%d %H:%M UTC')}" if user.suspended_until else ""
                    logout(request)
                    messages.warning(
                        request,
                        f"Your account is currently suspended{until_str}.{reason}",
                    )
                    return redirect(reverse("accounts:login"))

        return self.get_response(request)
