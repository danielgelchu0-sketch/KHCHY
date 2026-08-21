from django.conf import settings
from django.db import models


class MemberProfile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disabled', 'Disabled'),
    ]
    VOICE_CHOICES = [
        ('soprano', 'Soprano'),
        ('alto', 'Alto'),
        ('tenor', 'Tenor'),
        ('bass', 'Bass'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='member_profile',
    )
    full_name_en = models.CharField(max_length=255, verbose_name="Full Name (English)")
    full_name_am = models.CharField(max_length=255, blank=True, verbose_name="Full Name (Amharic)")
    phone_number = models.CharField(max_length=20, blank=True)
    voice_part = models.CharField(max_length=20, choices=VOICE_CHOICES, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    joined_at = models.DateTimeField(auto_now_add=True)

    VOICE_PARTS_AMHARIC = {
        'soprano': 'ሶፕራኖ (Soprano)',
        'alto': 'አልቶ (Alto)',
        'tenor': 'ቴነር (Tenor)',
        'bass': 'ባስ (Bass)',
    }
    STATUS_AMHARIC = {
        'pending': 'በመጠባበቅ ላይ ያለ',
        'approved': 'የጸደቀ',
        'rejected': 'ውድቅ የተደረገ',
        'disabled': 'የተሰናከለ',
    }

    class Meta:
        ordering = ['status', 'full_name_en']

    def __str__(self):
        return f"{self.full_name_en} ({self.get_status_display()})"

    def is_approved(self):
        return self.status == 'approved'

    def get_full_name(self, is_amharic=False):
        if is_amharic and self.full_name_am:
            return self.full_name_am
        return self.full_name_en

    def get_voice_part_name(self, is_amharic=False):
        if is_amharic:
            return self.VOICE_PARTS_AMHARIC.get(self.voice_part, self.get_voice_part_display())
        return self.get_voice_part_display()

    def get_status_name(self, is_amharic=False):
        if is_amharic:
            return self.STATUS_AMHARIC.get(self.status, self.get_status_display())
        return self.get_status_display()