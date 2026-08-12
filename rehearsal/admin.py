from django.contrib import admin
from .models import ChoirMember, RehearsalSession


@admin.register(ChoirMember)
class ChoirMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name_en', 'voice_part', 'phone_number', 'is_active', 'joined_date')
    list_filter = ('voice_part', 'is_active')
    search_fields = ('full_name_en', 'full_name_am', 'phone_number')


@admin.register(RehearsalSession)
class RehearsalSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location')
    list_filter = ('date',)
    filter_horizontal = ('attendees',)
    search_fields = ('title', 'notes_en', 'notes_am')