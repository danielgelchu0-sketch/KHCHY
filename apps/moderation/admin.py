from django.contrib import admin
from .models import AuditLog, Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "reporter", "status", "reviewed_by", "created_at")
    list_filter = ("category", "status", "created_at")
    search_fields = ("description", "resolution_note", "reporter__email", "reporter__display_name")
    raw_id_fields = ("reporter", "reviewed_by", "target_discussion", "target_reply", "target_user")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "moderator", "action", "target_repr", "target_user", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("target_repr", "reason", "moderator__email", "moderator__display_name")
    raw_id_fields = ("moderator", "target_user")
    readonly_fields = ("moderator", "action", "target_repr", "target_user", "reason", "metadata", "created_at")
