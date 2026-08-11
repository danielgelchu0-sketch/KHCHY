from django.contrib import admin
from .models import SiteSetting


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ("choir_name_en", "contact_email", "contact_phone")