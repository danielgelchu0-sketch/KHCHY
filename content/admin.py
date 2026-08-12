from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title_en', 'event_type', 'start_time', 'location')
    list_filter = ('event_type', 'start_time')
    search_fields = ('title_en', 'title_am', 'location', 'description_en')