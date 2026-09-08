from datetime import timedelta
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from apps.accounts.models import User
from apps.discussions.models import Discussion, Reply
from .forms import ModerationDecisionForm, ReportForm, UserSanctionForm
from .models import AuditLog, Report

logger = logging.getLogger(__name__)


def moderator_required(view_func):
    """Decorator ensuring only users with moderator role or higher can access view."""
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_moderator:
            logger.warning(f"Unauthorized moderation access attempt by user {request.user.id}")
            return HttpResponseForbidden("Access restricted to community moderators and administrators.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@method_decorator(login_required, name="dispatch")
class ReportSubmitView(View):
    """Allows community members to report a discussion, reply, or user."""

    def get(self, request):
        target_type = request.GET.get("type")
        target_id = request.GET.get("id")
        form = ReportForm()

        target_obj = None
        if target_type == "discussion":
            target_obj = get_object_or_404(Discussion, id=target_id)
        elif target_type == "reply":
            target_obj = get_object_or_404(Reply, id=target_id)
        elif target_type == "user":
            target_obj = get_object_or_404(User, id=target_id)
        else:
            messages.error(request, "Invalid report target.")
            return redirect("discussions:topic_list")

        return render(
            request,
            "moderation/report_form.html",
            {
                "form": form,
                "target_type": target_type,
                "target_id": target_id,
                "target_obj": target_obj,
            },
        )

    def post(self, request):
        target_type = request.POST.get("type")
        target_id = request.POST.get("id")
        form = ReportForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "moderation/report_form.html",
                {"form": form, "target_type": target_type, "target_id": target_id},
            )

        # Duplicate check to prevent report spamming
        existing_filter = Q(reporter=request.user, status__in=[Report.Status.PENDING, Report.Status.UNDER_REVIEW])
        if target_type == "discussion":
            target = get_object_or_404(Discussion, id=target_id)
            if Report.objects.filter(existing_filter, target_discussion=target).exists():
                messages.info(request, "You have already submitted a pending report for this discussion.")
                return redirect(target.get_absolute_url())
            report = form.save(commit=False)
            report.reporter = request.user
            report.target_discussion = target
            report.save()
            return_url = target.get_absolute_url()

        elif target_type == "reply":
            target = get_object_or_404(Reply, id=target_id)
            if Report.objects.filter(existing_filter, target_reply=target).exists():
                messages.info(request, "You have already submitted a pending report for this reply.")
                return redirect(target.discussion.get_absolute_url())
            report = form.save(commit=False)
            report.reporter = request.user
            report.target_reply = target
            report.save()
            return_url = target.discussion.get_absolute_url()

        elif target_type == "user":
            target = get_object_or_404(User, id=target_id)
            if target == request.user:
                messages.error(request, "You cannot report your own profile.")
                return redirect("core:home")
            if Report.objects.filter(existing_filter, target_user=target).exists():
                messages.info(request, "You have already submitted a pending report for this user.")
                return redirect("core:home")
            report = form.save(commit=False)
            report.reporter = request.user
            report.target_user = target
            report.save()
            return_url = reverse("accounts:public_profile", kwargs={"user_id": target.id})

        else:
            messages.error(request, "Invalid report target.")
            return redirect("discussions:topic_list")

        logger.info(f"Report #{report.id} ({report.category}) submitted by user {request.user.id}")
        messages.success(
            request,
            "Thank you for helping keep our church community safe. Your report has been submitted to moderators.",
        )
        return redirect(return_url)


@method_decorator(moderator_required, name="dispatch")
class ModeratorDashboardView(View):
    """
    Central moderation control center for reviewing reports, managing flagged content,
    and monitoring community health.
    """

    def get(self, request):
        status_filter = request.GET.get("status", "pending")
        reports_qs = Report.objects.select_related(
            "reporter",
            "target_discussion",
            "target_discussion__author",
            "target_reply",
            "target_reply__author",
            "target_reply__discussion",
            "target_user",
        )

        if status_filter != "all":
            reports_qs = reports_qs.filter(status=status_filter)

        paginator = Paginator(reports_qs, 15)
        page_obj = paginator.get_page(request.GET.get("page"))

        # Aggregate community statistics
        stats = {
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(status=User.AccountStatus.ACTIVE).count(),
            "suspended_users": User.objects.filter(status=User.AccountStatus.SUSPENDED).count(),
            "banned_users": User.objects.filter(status=User.AccountStatus.BANNED).count(),
            "total_discussions": Discussion.objects.count(),
            "anonymous_discussions": Discussion.objects.filter(is_anonymous=True).count(),
            "total_replies": Reply.objects.count(),
            "anonymous_replies": Reply.objects.filter(is_anonymous=True).count(),
            "pending_reports": Report.objects.filter(status=Report.Status.PENDING).count(),
            "under_review_reports": Report.objects.filter(status=Report.Status.UNDER_REVIEW).count(),
        }

        recent_actions = AuditLog.objects.select_related("moderator", "target_user").order_by("-created_at")[:10]

        return render(
            request,
            "moderation/dashboard.html",
            {
                "stats": stats,
                "page_obj": page_obj,
                "status_filter": status_filter,
                "recent_actions": recent_actions,
            },
        )


@method_decorator(moderator_required, name="dispatch")
class ReportDetailView(View):
    """
    Detailed inspection of a reported item.
    Moderators are authorized to see the true internal author identity to protect community safety.
    """

    def get(self, request, pk):
        report = get_object_or_404(
            Report.objects.select_related(
                "reporter",
                "reviewed_by",
                "target_discussion",
                "target_discussion__author",
                "target_discussion__topic",
                "target_reply",
                "target_reply__author",
                "target_reply__discussion",
                "target_user",
            ),
            pk=pk,
        )

        # Mark as under review if pending
        if report.status == Report.Status.PENDING:
            report.status = Report.Status.UNDER_REVIEW
            report.save(update_fields=["status"])

        decision_form = ModerationDecisionForm()
        sanction_form = UserSanctionForm()

        return render(
            request,
            "moderation/report_detail.html",
            {
                "report": report,
                "decision_form": decision_form,
                "sanction_form": sanction_form,
                "internal_author": report.get_target_internal_author(),
            },
        )

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        decision_form = ModerationDecisionForm(request.POST)

        if decision_form.is_valid():
            action = decision_form.cleaned_data["action"]
            note = decision_form.cleaned_data["resolution_note"]

            with transaction.atomic():
                if action == "resolve":
                    report.status = Report.Status.RESOLVED
                    audit_action = AuditLog.ActionType.RESOLVE_REPORT
                else:
                    report.status = Report.Status.DISMISSED
                    audit_action = AuditLog.ActionType.DISMISS_REPORT

                report.reviewed_by = request.user
                report.resolution_note = note
                report.save()

                AuditLog.objects.create(
                    moderator=request.user,
                    action=audit_action,
                    target_repr=report.get_target_repr(),
                    target_user=report.get_target_internal_author(),
                    reason=note,
                )

            messages.success(request, f"Report #{report.id} marked as {report.get_status_display()}.")
            return redirect("moderation:dashboard")

        return self.get(request, pk)


@method_decorator(moderator_required, name="dispatch")
class DiscussionModerationActionView(View):
    """Moderator actions on a discussion: hide, restore, lock, unlock."""

    def post(self, request, pk):
        discussion = get_object_or_404(Discussion, pk=pk)
        action = request.POST.get("action")
        reason = request.POST.get("reason", "").strip() or "Moderator action applied."

        with transaction.atomic():
            if action == "hide":
                discussion.status = Discussion.Status.HIDDEN
                AuditLog.objects.create(
                    moderator=request.user,
                    action=AuditLog.ActionType.HIDE_DISCUSSION,
                    target_repr=f"Discussion: {discussion.title}",
                    target_user=discussion.author,
                    reason=reason,
                )
                messages.warning(request, f"Discussion '{discussion.title}' has been hidden from community members.")

            elif action == "restore":
                discussion.status = Discussion.Status.ACTIVE
                AuditLog.objects.create(
                    moderator=request.user,
                    action=AuditLog.ActionType.RESTORE_DISCUSSION,
                    target_repr=f"Discussion: {discussion.title}",
                    target_user=discussion.author,
                    reason=reason,
                )
                messages.success(request, f"Discussion '{discussion.title}' has been restored.")

            elif action == "lock":
                discussion.status = Discussion.Status.LOCKED
                AuditLog.objects.create(
                    moderator=request.user,
                    action=AuditLog.ActionType.LOCK_DISCUSSION,
                    target_repr=f"Discussion: {discussion.title}",
                    target_user=discussion.author,
                    reason=reason,
                )
                messages.warning(request, f"Discussion '{discussion.title}' is now locked.")

            elif action == "unlock":
                discussion.status = Discussion.Status.ACTIVE
                AuditLog.objects.create(
                    moderator=request.user,
                    action=AuditLog.ActionType.UNLOCK_DISCUSSION,
                    target_repr=f"Discussion: {discussion.title}",
                    target_user=discussion.author,
                    reason=reason,
                )
                messages.success(request, f"Discussion '{discussion.title}' is now unlocked.")

            discussion.save(update_fields=["status"])

        return redirect(discussion.get_absolute_url())


@method_decorator(moderator_required, name="dispatch")
class ReplyModerationActionView(View):
    """Moderator actions on replies: hide or restore."""

    def post(self, request, pk):
        reply = get_object_or_404(Reply, pk=pk)
        action = request.POST.get("action")
        reason = request.POST.get("reason", "").strip() or "Moderator action applied."

        with transaction.atomic():
            if action == "hide":
                reply.status = Reply.Status.HIDDEN
                AuditLog.objects.create(
                    moderator=request.user,
                    action=AuditLog.ActionType.HIDE_REPLY,
                    target_repr=f"Reply #{reply.id} in {reply.discussion.title}",
                    target_user=reply.author,
                    reason=reason,
                )
                messages.warning(request, "Reply has been hidden from public view.")

            elif action == "restore":
                reply.status = Reply.Status.ACTIVE
                AuditLog.objects.create(
                    moderator=request.user,
                    action=AuditLog.ActionType.RESTORE_REPLY,
                    target_repr=f"Reply #{reply.id} in {reply.discussion.title}",
                    target_user=reply.author,
                    reason=reason,
                )
                messages.success(request, "Reply has been restored.")

            reply.save(update_fields=["status"])

        return redirect(reply.discussion.get_absolute_url())


@method_decorator(moderator_required, name="dispatch")
class UserSanctionView(View):
    """Applies warnings, suspensions, or bans to a user account."""

    def post(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        if target_user.is_administrator or target_user.is_superuser:
            messages.error(request, "Administrators cannot be sanctioned through this interface.")
            return redirect("moderation:dashboard")

        form = UserSanctionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            reason = form.cleaned_data["reason"]

            with transaction.atomic():
                if action == "warn":
                    AuditLog.objects.create(
                        moderator=request.user,
                        action=AuditLog.ActionType.WARN_USER,
                        target_repr=f"User {target_user.display_name}",
                        target_user=target_user,
                        reason=reason,
                    )
                    # Create notification for user
                    from apps.notifications.models import Notification
                    Notification.objects.create(
                        recipient=target_user,
                        title="Formal Community Warning",
                        message=f"A community moderator issued a warning regarding your recent activity: {reason}",
                        link=reverse("discussions:topic_list"),
                        notification_type=Notification.NotificationType.MODERATION,
                    )
                    messages.warning(request, f"Warning issued to {target_user.display_name}.")

                elif action.startswith("suspend_"):
                    days = int(action.split("_")[1])
                    target_user.status = User.AccountStatus.SUSPENDED
                    target_user.suspension_reason = reason
                    target_user.suspended_until = timezone.now() + timedelta(days=days)
                    target_user.save(update_fields=["status", "suspension_reason", "suspended_until"])

                    AuditLog.objects.create(
                        moderator=request.user,
                        action=AuditLog.ActionType.SUSPEND_USER,
                        target_repr=f"User {target_user.display_name} ({days} days)",
                        target_user=target_user,
                        reason=reason,
                    )
                    messages.error(request, f"Account for {target_user.display_name} suspended for {days} days.")

                elif action == "ban":
                    target_user.status = User.AccountStatus.BANNED
                    target_user.suspension_reason = reason
                    target_user.suspended_until = None
                    target_user.save(update_fields=["status", "suspension_reason", "suspended_until"])

                    AuditLog.objects.create(
                        moderator=request.user,
                        action=AuditLog.ActionType.BAN_USER,
                        target_repr=f"User {target_user.display_name}",
                        target_user=target_user,
                        reason=reason,
                    )
                    messages.error(request, f"Account for {target_user.display_name} has been permanently banned.")

                elif action == "unban":
                    target_user.status = User.AccountStatus.ACTIVE
                    target_user.suspension_reason = ""
                    target_user.suspended_until = None
                    target_user.save(update_fields=["status", "suspension_reason", "suspended_until"])

                    AuditLog.objects.create(
                        moderator=request.user,
                        action=AuditLog.ActionType.UNBAN_USER,
                        target_repr=f"User {target_user.display_name}",
                        target_user=target_user,
                        reason=reason,
                    )
                    messages.success(request, f"Account for {target_user.display_name} restored to active.")

        return redirect("moderation:dashboard")


@method_decorator(moderator_required, name="dispatch")
class AuditLogListView(View):
    """Searchable chronological history of all moderation actions."""

    def get(self, request):
        logs_qs = AuditLog.objects.select_related("moderator", "target_user").order_by("-created_at")

        search_query = request.GET.get("q", "").strip()
        if search_query:
            logs_qs = logs_qs.filter(
                Q(target_repr__icontains=search_query)
                | Q(reason__icontains=search_query)
                | Q(moderator__display_name__icontains=search_query)
                | Q(target_user__display_name__icontains=search_query)
            )

        paginator = Paginator(logs_qs, 25)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(
            request,
            "moderation/audit_log.html",
            {"page_obj": page_obj, "search_query": search_query},
        )
