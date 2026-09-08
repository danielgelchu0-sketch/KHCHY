from django import forms
from django.core.exceptions import ValidationError
from .models import Discussion, Reply, Topic


class DiscussionCreateForm(forms.ModelForm):
    """Form to ask a question or start a discussion thread."""

    POST_MODE_CHOICES = [
        ("identified", "Post with my identity"),
        ("anonymous", "Post anonymously"),
    ]

    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-input form-title-input",
                "placeholder": "What question or topic would you like to explore?",
                "autocomplete": "off",
            }
        ),
        label="Discussion Title / Question",
        help_text="Be clear and descriptive so community members can give helpful biblical insight and guidance.",
    )
    content = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 6,
                "placeholder": "Provide context, your thoughts, or specific background about your question...",
            }
        ),
        label="Context & Details",
    )
    post_mode = forms.ChoiceField(
        choices=POST_MODE_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "post-mode-radio"}),
        initial="identified",
        label="How would you like to post?",
        help_text="Choose whether other members see your community identity or if your post should be presented anonymously.",
        error_messages={
            "invalid_choice": "You must select a valid posting identity mode.",
        },
    )

    class Meta:
        model = Discussion
        fields = ["title", "content"]

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 5:
            raise ValidationError("Discussion title must be at least 5 characters long.")
        return title

    def clean_content(self):
        content = self.cleaned_data.get("content", "").strip()
        if len(content) < 10:
            raise ValidationError("Please provide at least 10 characters of context.")
        return content

    def clean(self):
        cleaned_data = super().clean()
        if "post_mode" not in self.errors:
            mode = cleaned_data.get("post_mode")
            if mode not in ["identified", "anonymous"]:
                self.add_error("post_mode", "You must select a valid posting identity mode.")
        return cleaned_data


class ReplyCreateForm(forms.ModelForm):
    """Form to answer a question or post a threaded reply."""

    POST_MODE_CHOICES = [
        ("identified", "Post with my identity"),
        ("anonymous", "Post anonymously"),
    ]

    content = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 4,
                "placeholder": "Write your reply, guidance, or question response...",
            }
        ),
        label="Your Reply",
    )
    parent_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )
    post_mode = forms.ChoiceField(
        choices=POST_MODE_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "post-mode-radio"}),
        initial="identified",
        label="How would you like to post?",
        error_messages={
            "invalid_choice": "You must select a valid posting identity mode.",
        },
    )

    class Meta:
        model = Reply
        fields = ["content"]

    def clean_content(self):
        content = self.cleaned_data.get("content", "").strip()
        if len(content) < 3:
            raise ValidationError("Reply must contain at least 3 characters.")
        return content

    def clean_parent_id(self):
        parent_id = self.cleaned_data.get("parent_id")
        if parent_id:
            try:
                parent = Reply.objects.get(id=parent_id)
                return parent
            except Reply.DoesNotExist:
                raise ValidationError("The parent reply you are attempting to respond to does not exist.")
        return None


class TopicAdminForm(forms.ModelForm):
    """Form for administrators to create and manage topic rooms."""

    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-input"}),
        label="Topic Name",
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 3}),
        label="Topic Description",
    )
    icon = forms.CharField(
        max_length=50,
        initial="chat",
        widget=forms.TextInput(attrs={"class": "form-input"}),
        label="Icon Key",
        help_text="e.g. faith, youth, marriage, heart, book, church",
    )
    order = forms.IntegerField(
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-input"}),
        label="Display Order",
    )
    is_archived = forms.BooleanField(
        required=False,
        label="Archive this topic (read-only for new discussions)",
    )

    class Meta:
        model = Topic
        fields = ["name", "description", "icon", "order", "is_archived"]
