from django.db import models


class Event(models.Model):
    EVENT_TYPE_CHOICES = [
        ('service', 'Sunday Service'),
        ('rehearsal', 'Choir Rehearsal'),
        ('concert', 'Concert / Special Event'),
        ('outreach', 'Outreach / Ministry'),
    ]

    title_en = models.CharField(max_length=255, verbose_name="Title (English)")
    title_am = models.CharField(max_length=255, blank=True, verbose_name="Title (Amharic)")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='service')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=255, default="Horbabicho Kalehiwot Church")
    description_en = models.TextField(blank=True, verbose_name="Description (English)")
    description_am = models.TextField(blank=True, verbose_name="Description (Amharic)")
    banner_image = models.ImageField(upload_to="events/banners/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    EVENT_TYPE_AMHARIC = {
        'service': 'የእሑድ አገልግሎት',
        'rehearsal': 'የኳየር ልምምድ',
        'concert': 'ኮንሰርት / ልዩ ዝግጅት',
        'outreach': 'የወንጌል አገልግሎት / ጉዞ',
    }

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title_en} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"

    def get_title(self, is_amharic=False):
        if is_amharic and self.title_am:
            return self.title_am
        return self.title_en

    def get_description(self, is_amharic=False):
        if is_amharic and self.description_am:
            return self.description_am
        return self.description_en

    def get_event_type_name(self, is_amharic=False):
        if is_amharic:
            return self.EVENT_TYPE_AMHARIC.get(self.event_type, self.get_event_type_display())
        return self.get_event_type_display()