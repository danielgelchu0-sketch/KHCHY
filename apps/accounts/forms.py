import os
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Profile


class UserRegistrationForm(forms.ModelForm):
    """Registration form for new church community members."""

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "you@example.com", "autocomplete": "email"}
        ),
        label="Email Address",
        help_text="Your email will never be displayed publicly to other members.",
    )
    display_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "Your Display Name", "autocomplete": "name"}
        ),
        label="Community Display Name",
        help_text="This name is shown when you choose to post with your identity.",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Create a secure password", "autocomplete": "new-password"}
        ),
        label="Password",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Confirm password", "autocomplete": "new-password"}
        ),
        label="Confirm Password",
    )
    agree_to_guidelines = forms.BooleanField(
        required=True,
        label="I agree to the Community Guidelines & Privacy Disclosure",
        help_text="I understand that sensitive questions can be posted anonymously to other members, while moderators retain internal safety review capabilities.",
    )

    class Meta:
        model = User
        fields = ["email", "display_name"]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_display_name(self):
        name = self.cleaned_data.get("display_name", "").strip()
        if len(name) < 2:
            raise ValidationError("Display name must be at least 2 characters long.")
        if "admin" in name.lower() or "moderator" in name.lower() or "anonymous" in name.lower():
            raise ValidationError("Display name cannot contain reserved words (admin, moderator, anonymous).")
        return name

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
            else:
                validate_password(password)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = User.Role.MEMBER
        user.status = User.AccountStatus.ACTIVE
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    """Authentication form for logging in members via email or display name."""

    email = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "you@example.com or Display Name",
                "autocomplete": "username",
            }
        ),
        label="Email Address or Display Name",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Your password", "autocomplete": "current-password"}
        ),
        label="Password",
    )

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("email", "").strip()
        password = cleaned_data.get("password")

        if identifier and password:
            self.user_cache = authenticate(username=identifier, password=password)
            if self.user_cache is None:
                raise ValidationError("Invalid email address or password.")
            elif not self.user_cache.is_active or self.user_cache.status == User.AccountStatus.BANNED:
                raise ValidationError("This account has been deactivated or banned.")
            elif self.user_cache.status == User.AccountStatus.SUSPENDED:
                if not self.user_cache.is_account_active:
                    raise ValidationError("This account is currently suspended.")

        return cleaned_data

    def get_user(self):
        return getattr(self, "user_cache", None)


class UserProfileForm(forms.ModelForm):
    """Form to edit user's display name, email, bio, and avatar."""

    display_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-input", "autocomplete": "name"}),
        label="Display Name",
        help_text="Public community name shown when posting with your identity.",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-input", "autocomplete": "email"}),
        label="Email Address",
        help_text="Your private account login email address.",
    )
    bio = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "A brief introduction..."}),
        label="Bio",
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-file"}),
        label="Profile Photo (Max 2MB, JPG/PNG/WEBP)",
    )

    class Meta:
        model = Profile
        fields = ["bio", "avatar"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["display_name"].initial = self.user.display_name
            self.fields["email"].initial = self.user.email

    def clean_display_name(self):
        name = self.cleaned_data.get("display_name", "").strip()
        if len(name) < 2:
            raise ValidationError("Display name must be at least 2 characters long.")
        if "admin" in name.lower() or "moderator" in name.lower() or "anonymous" in name.lower():
            raise ValidationError("Display name cannot contain reserved words.")
        return name

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise ValidationError("Email address cannot be empty.")
        existing = User.objects.filter(email__iexact=email)
        if self.user:
            existing = existing.exclude(id=self.user.id)
        if existing.exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and hasattr(avatar, "size"):
            # 1. Enforce 2MB size limit
            if avatar.size > 2 * 1024 * 1024:
                raise ValidationError("Profile photo must be smaller than 2MB.")
            # 2. Enforce allowed extension
            ext = os.path.splitext(avatar.name)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                raise ValidationError("Profile photo must be a JPG, PNG, or WEBP image file.")
            # 3. Validate image integrity with Pillow
            try:
                from PIL import Image
                img = Image.open(avatar)
                img.verify()
                if img.format.lower() not in ["jpeg", "png", "webp"]:
                    raise ValidationError("Uploaded file is not a recognized JPEG, PNG, or WEBP image.")
            except Exception:
                raise ValidationError("Invalid or corrupted image file.")
        return avatar

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.display_name = self.cleaned_data["display_name"]
            if "email" in self.cleaned_data:
                self.user.email = self.cleaned_data["email"]
            if commit:
                self.user.save(update_fields=["display_name", "email"])
        if commit:
            profile.save()
        return profile
