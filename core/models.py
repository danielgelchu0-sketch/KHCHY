from django.db import models


class SiteSetting(models.Model):
    choir_name_en = models.CharField(
        max_length=255,
        default="Horbabicho Kalehiwot Church Yahiwenis Choir"
    )
    choir_name_am = models.CharField(
        max_length=255,
        default="ሆርባቢቾ ቃለ ሕይወት ቤተክርስቲያን ያህዌ ንሲ ኳየር"
    )
    hero_banner = models.ImageField(
        upload_to="branding/",
        blank=True,
        null=True,
        help_text="Header image displayed at the top of the home page."
    )
    about_text_en = models.TextField(blank=True)
    about_text_am = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.choir_name_en

    def get_choir_name(self, is_amharic=False):
        if is_amharic and self.choir_name_am:
            return self.choir_name_am
        return self.choir_name_en

    def get_about_text(self, is_amharic=False):
        if is_amharic and self.about_text_am:
            return self.about_text_am
        return self.about_text_en