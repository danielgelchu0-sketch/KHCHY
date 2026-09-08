import os
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier for authentication."""

    def create_user(self, email, password=None, display_name=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required.")
        email = self.normalize_email(email).lower()
        if not display_name:
            display_name = email.split("@")[0].capitalize()
        user = self.model(email=email, display_name=display_name, **extra_fields)
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

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

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
