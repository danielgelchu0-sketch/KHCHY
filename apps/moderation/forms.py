from django import forms
from django.core.exceptions import ValidationError
from .models import AuditLog, Report


class ReportForm(forms.ModelForm):
    """Form used by community members to flag inappropriate content or behavior."""

    category = forms.ChoiceField(
        choices=Report.Category.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Why are you reporting this?",
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 3,
                "placeholder": "Optional: describe why this content violates community guidelines...",
            }
        ),
        label="Additional Details",
    )

    class Meta:
        model = Report
        fields = ["category", "description"]


class ModerationDecisionForm(forms.Form):
    """Form used by moderators when acting on reports or content."""

    action = forms.ChoiceField(
        choices=[
            ("resolve", "Resolve Report (Violation found & action taken)"),
            ("dismiss", "Dismiss Report (No violation found)"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Resolution Decision",
    )
    resolution_note = forms.CharField(
        widget=forms.Textarea(
            attrs={"class": "form-textarea", "rows": 3, "placeholder": "Internal note explaining the decision..."}
        ),
        label="Moderator Note",
        required=True,
    )


class UserSanctionForm(forms.Form):
    """Form to warn, suspend, or ban a user."""

    ACTION_CHOICES = [
        ("warn", "Issue Formal Warning"),
        ("suspend_1", "Suspend for 24 Hours"),
        ("suspend_7", "Suspend for 7 Days"),
        ("suspend_30", "Suspend for 30 Days"),
        ("ban", "Permanent Community Ban"),
        ("unban", "Restore Account to Active"),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Sanction Action",
    )
    reason = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 3,
                "placeholder": "State the exact guideline violation and reasoning for this sanction...",
            }
        ),
        label="Reason for Action",
        required=True,
    )
