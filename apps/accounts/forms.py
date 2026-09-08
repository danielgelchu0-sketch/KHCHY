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
    """Authentication form for logging in members."""

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "you@example.com", "autocomplete": "email"}
        ),
        label="Email Address",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Your password", "autocomplete": "current-password"}
        ),
        label="Password",
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").strip().lower()
        password = cleaned_data.get("password")

        if email and password:
            self.user_cache = authenticate(username=email, password=password)
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
    """Form to edit user's display name, bio, and avatar."""

    display_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-input"}),
        label="Display Name",
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

    def clean_display_name(self):
        name = self.cleaned_data.get("display_name", "").strip()
        if len(name) < 2:
            raise ValidationError("Display name must be at least 2 characters long.")
        if "admin" in name.lower() or "moderator" in name.lower() or "anonymous" in name.lower():
            raise ValidationError("Display name cannot contain reserved words.")
        return name

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.display_name = self.cleaned_data["display_name"]
            if commit:
                self.user.save(update_fields=["display_name"])
        if commit:
            profile.save()
        return profile
