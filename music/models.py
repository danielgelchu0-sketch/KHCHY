import re
from django.db import models

class Album(models.Model):
    title_en = models.CharField(max_length=255, verbose_name="Title (English)")
    title_am = models.CharField(max_length=255, blank=True, verbose_name="Title (Amharic)")
    cover_image = models.ImageField(upload_to="albums/covers/", blank=True, null=True)
    release_year = models.PositiveIntegerField(blank=True, null=True)
    description_en = models.TextField(blank=True, verbose_name="Description (English)")
    description_am = models.TextField(blank=True, verbose_name="Description (Amharic)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-release_year', '-created_at']

    def __str__(self):
        return self.title_en


class Song(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='songs')
    track_number = models.PositiveIntegerField(default=1)
    title_en = models.CharField(max_length=255, verbose_name="Title (English)")
    title_am = models.CharField(max_length=255, blank=True, verbose_name="Title (Amharic)")
    audio_file = models.FileField(upload_to="songs/audio/", blank=True, null=True, help_text="Upload MP3 or WAV")
    youtube_url = models.URLField(blank=True, help_text="Link to YouTube video (optional)")
    lyrics_en = models.TextField(blank=True, verbose_name="Lyrics (English)")
    lyrics_am = models.TextField(blank=True, verbose_name="Lyrics (Amharic)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['track_number', 'id']

    def __str__(self):
        return f"{self.track_number}. {self.title_en}"