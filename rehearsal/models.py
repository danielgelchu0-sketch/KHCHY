from django.db import models
from django.conf import settings


class ChoirMember(models.Model):
    VOICE_PARTS = [
        ('soprano', 'Soprano'),
        ('alto', 'Alto'),
        ('tenor', 'Tenor'),
        ('bass', 'Bass'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='choir_profile',
        blank=True, null=True
    )
    full_name_en = models.CharField(max_length=255, verbose_name="Full Name (English)")
    full_name_am = models.CharField(max_length=255, blank=True, verbose_name="Full Name (Amharic)")
    voice_part = models.CharField(max_length=20, choices=VOICE_PARTS)
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    joined_date = models.DateField(auto_now_add=True)

    VOICE_PARTS_AMHARIC = {
        'soprano': 'ሶፕራኖ (Soprano)',
        'alto': 'አልቶ (Alto)',
        'tenor': 'ቴነር (Tenor)',
        'bass': 'ባስ (Bass)',
    }

    class Meta:
        ordering = ['voice_part', 'full_name_en']

    def __str__(self):
        return f"{self.full_name_en} ({self.get_voice_part_display()})"

    def get_full_name(self, is_amharic=False):
        if is_amharic and self.full_name_am:
            return self.full_name_am
        return self.full_name_en

    def get_voice_part_name(self, is_amharic=False):
        if is_amharic:
            return self.VOICE_PARTS_AMHARIC.get(self.voice_part, self.get_voice_part_display())
        return self.get_voice_part_display()


class RehearsalSession(models.Model):
    title = models.CharField(max_length=255, default="Weekly Rehearsal")
    date = models.DateTimeField()
    location = models.CharField(max_length=255, default="Church Choir Room")
    notes_en = models.TextField(blank=True, verbose_name="Notes / Agenda (English)")
    notes_am = models.TextField(blank=True, verbose_name="Notes / Agenda (Amharic)")
    sheet_music = models.FileField(upload_to="rehearsals/sheets/", blank=True, null=True)
    attendees = models.ManyToManyField(ChoirMember, blank=True, related_name='rehearsals_attended')

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.title} - {self.date.strftime('%Y-%m-%d %H:%M')}"

    def get_title_lang(self, is_amharic=False):
        if is_amharic:
            if self.title.strip() == "Weekly Rehearsal":
                return "ሳምንታዊ የልምምድ ፕሮግራም"
        return self.title

    def get_notes(self, is_amharic=False):
        if is_amharic and self.notes_am:
            return self.notes_am
        return self.notes_en