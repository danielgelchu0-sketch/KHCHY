import os
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager where email or phone number serves as identifier for authentication."""

    def create_user(self, email=None, password=None, display_name=None, phone_number=None, **extra_fields):
        phone_number = (phone_number or "").strip()
        if not email and not phone_number:
            raise ValueError("An email address or phone number is required.")
        if not email and phone_number:
            clean_digits = "".join(filter(str.isdigit, phone_number))
            email = f"phone_{clean_digits}@phone.community.hkhc.org"
        email = self.normalize_email(email).lower()
        if not display_name:
            display_name = phone_number if phone_number else email.split("@")[0].capitalize()
        user = self.model(email=email, display_name=display_name, phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMINISTRATOR)
        extra_fields.setdefault("status", User.AccountStatus.ACTIVE)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


def avatar_upload_path(instance, filename):
    """Generate safe unique filename for user profile pictures."""
    ext = filename.split(".")[-1].lower()
    unique_id = uuid.uuid4().hex[:12]
    return f"avatars/{instance.user.id}_{unique_id}.{ext}"


def validate_avatar_file(value):
    """Validate uploaded avatar image file size and extension."""
    valid_extensions = ["jpg", "jpeg", "png", "webp"]
    ext = os.path.splitext(value.name)[1][1:].lower()
    if ext not in valid_extensions:
        raise ValidationError("Unsupported file extension. Allowed formats: JPG, JPEG, PNG, WEBP.")

    max_size = 2 * 1024 * 1024  # 2MB
    if value.size > max_size:
        raise ValidationError("Profile photo file size cannot exceed 2MB.")


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for HKHC community members.
    Email is used for authentication; display_name is used for public presentation.
    """

    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        MODERATOR = "moderator", "Moderator"
        ADMINISTRATOR = "administrator", "Administrator"

    class AccountStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        BANNED = "banned", "Banned"

    email = models.EmailField("Email Address", unique=True, db_index=True)
    phone_number = models.CharField(
        "Phone Number",
        max_length=30,
        blank=True,
        default="",
        db_index=True,
        help_text="Optional mobile phone number for authentication and notifications.",
    )
    display_name = models.CharField(
        "Display Name",
        max_length=50,
        help_text="Public community display name visible to other members.",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    suspension_reason = models.TextField(blank=True, default="")
    suspended_until = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    referral_code = models.CharField(
        "Referral Code",
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        help_text="Unique referral/invite code for inviting friends.",
    )
    invited_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_members",
        help_text="Member who invited this user.",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        super().save(*args, **kwargs)

    @classmethod
    def generate_referral_code(cls):
        import secrets
        import string
        chars = string.ascii_uppercase + string.digits
        for _ in range(25):
            code = "".join(secrets.choice(chars) for _ in range(8))
            if not cls.objects.filter(referral_code=code).exists():
                return code
        return secrets.token_hex(4).upper()

    @property
    def invited_members_count(self):
        """Count of active members who registered using this member's referral code."""
        return self.invited_members.filter(is_active=True).count()


    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.display_name} ({self.email})"

    @property
    def is_moderator(self):
        """Check if user has moderator privileges."""
        return self.role in (self.Role.MODERATOR, self.Role.ADMINISTRATOR) or self.is_superuser

    @property
    def is_administrator(self):
        """Check if user has administrator privileges."""
        return self.role == self.Role.ADMINISTRATOR or self.is_superuser

    @property
    def is_account_active(self):
        """Check if account is active and not suspended or banned."""
        if not self.is_active:
            return False
        if self.status == self.AccountStatus.BANNED:
            return False
        if self.status == self.AccountStatus.SUSPENDED:
            if self.suspended_until and timezone.now() > self.suspended_until:
                # Suspension expired, automatically treat as active
                return True
            return False
        return True

    def can_post(self):
        """Returns True if the user is authorized to create questions or replies."""
        return self.is_account_active


class Profile(models.Model):
    """User profile storing personal info, bio, and avatar."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, max_length=500, default="")
    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        validators=[validate_avatar_file],
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.display_name}"
