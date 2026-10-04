import os
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Profile


class UserRegistrationForm(forms.ModelForm):
    """Registration form for new church community members supporting email or phone."""

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "you@example.com (optional if phone provided)", "autocomplete": "email"}
        ),
        label="Email Address",
        help_text="Your email will never be displayed publicly. Optional if phone number is provided.",
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "e.g. 0911223344 or +251...", "autocomplete": "tel"}
        ),
        label="Phone Number",
        help_text="Optional if email is provided. Makes signing in fast and easy.",
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
            attrs={"class": "form-input", "placeholder": "At least 4 characters", "autocomplete": "new-password"}
        ),
        label="Password",
        help_text="At least 4 characters.",
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
        fields = ["email", "phone_number", "display_name"]

    def clean_display_name(self):
        name = self.cleaned_data.get("display_name", "").strip()
        if len(name) < 2:
            raise ValidationError("Display name must be at least 2 characters long.")
        if "admin" in name.lower() or "moderator" in name.lower() or "anonymous" in name.lower():
            raise ValidationError("Display name cannot contain reserved words (admin, moderator, anonymous).")
        return name

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").strip().lower()
        phone = cleaned_data.get("phone_number", "").strip()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # Validate that at least one of email or phone is provided
        if not email and not phone:
            raise ValidationError("Please provide either an email address or a phone number to register.")

        if email:
            if User.objects.filter(email__iexact=email).exists():
                self.add_error("email", "An account with this email address already exists.")
            cleaned_data["email"] = email

        if phone:
            clean_digits = "".join(filter(str.isdigit, phone))
            if len(clean_digits) < 7:
                self.add_error("phone_number", "Please enter a valid phone number (at least 7 digits).")
            else:
                for existing in User.objects.exclude(phone_number=""):
                    existing_digits = "".join(filter(str.isdigit, existing.phone_number))
                    if existing_digits and (existing_digits == clean_digits or existing_digits.endswith(clean_digits[-9:]) or clean_digits.endswith(existing_digits[-9:])):
                        self.add_error("phone_number", "An account with this phone number already exists.")
                        break

        # If user registered with phone only, generate internal email
        if not email and phone:
            clean_digits = "".join(filter(str.isdigit, phone))
            cleaned_data["email"] = f"phone_{clean_digits}@phone.community.hkhc.org"

        if password and confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
            elif len(password) < 4:
                self.add_error("password", "Password must be at least 4 characters long.")
            else:
                validate_password(password)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data.get("phone_number", "").strip()
        user.set_password(self.cleaned_data["password"])
        user.role = User.Role.MEMBER
        user.status = User.AccountStatus.ACTIVE
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    """Authentication form for logging in members via email, phone, or display name."""

    email = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "you@example.com, Phone (09...), or Display Name",
                "autocomplete": "username",
            }
        ),
        label="Email Address, Phone Number, or Display Name",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Your password", "autocomplete": "current-password"}
        ),
        label="Password",
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        label="Keep me signed in on this device",
    )

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("email", "").strip()
        password = cleaned_data.get("password")

        if identifier and password:
            self.user_cache = authenticate(username=identifier, password=password)
            if self.user_cache is None:
                raise ValidationError("Invalid email address or password. Please check your credentials or click 'Forgot password?'.")
            elif not self.user_cache.is_active or self.user_cache.status == User.AccountStatus.BANNED:
                raise ValidationError("This account has been deactivated or banned.")
            elif self.user_cache.status == User.AccountStatus.SUSPENDED:
                if not self.user_cache.is_account_active:
                    raise ValidationError("This account is currently suspended.")

        return cleaned_data

    def get_user(self):
        return getattr(self, "user_cache", None)


class UserProfileForm(forms.ModelForm):
    """Form to edit user's display name, email, phone number, bio, and avatar."""

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
    phone_number = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "autocomplete": "tel"}),
        label="Phone Number",
        help_text="Optional mobile phone number for authentication.",
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
            self.fields["phone_number"].initial = self.user.phone_number

    def clean_display_name(self):
        name = self.cleaned_data.get("display_name", "").strip()
        if len(name) < 2:
            raise ValidationError("Display name must be at least 2 characters long.")
        if "admin" in name.lower() or "moderator" in name.lower() or "anonymous" in name.lower():
            raise ValidationError("Display name cannot contain reserved words.")
        return name

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number", "").strip()
        if phone:
            clean_digits = "".join(filter(str.isdigit, phone))
            if len(clean_digits) < 7:
                raise ValidationError("Please enter a valid phone number (at least 7 digits).")
            existing = User.objects.exclude(phone_number="")
            if self.user:
                existing = existing.exclude(id=self.user.id)
            for cand in existing:
                cand_digits = "".join(filter(str.isdigit, cand.phone_number))
                if cand_digits and (cand_digits == clean_digits or cand_digits.endswith(clean_digits[-9:]) or clean_digits.endswith(cand_digits[-9:])):
                    raise ValidationError("An account with this phone number already exists.")
        return phone

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
            if "phone_number" in self.cleaned_data:
                self.user.phone_number = self.cleaned_data["phone_number"]
            if commit:
                self.user.save(update_fields=["display_name", "email", "phone_number"])
        if commit:
            profile.save()
        return profile
