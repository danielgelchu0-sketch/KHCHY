from django.contrib import admin
from .models import MemberProfile


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name_en', 'voice_part', 'status', 'joined_at']
    list_filter = ['status', 'voice_part']
    search_fields = ['full_name_en', 'full_name_am', 'phone_number', 'user__username']
    actions = ['approve_members', 'disable_members']

    def approve_members(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f"{updated} member(s) approved.")
    approve_members.short_description = "Approve selected members"

    def disable_members(self, request, queryset):
        updated = queryset.update(status='disabled')
        self.message_user(request, f"{updated} member(s) disabled.")
    disable_members.short_description = "Disable selected members"