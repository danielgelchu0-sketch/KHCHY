from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ("email", "display_name", "role", "status", "is_staff", "date_joined")
    list_filter = ("role", "status", "is_staff", "is_superuser")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Community Identity", {"fields": ("display_name", "role")}),
        ("Account Status", {"fields": ("status", "suspension_reason", "suspended_until", "is_active")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password", "role", "status"),
            },
        ),
    )
    search_fields = ("email", "display_name")
    ordering = ("-date_joined",)
