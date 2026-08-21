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

    def get_title(self, is_amharic=False):
        if is_amharic and self.title_am:
            return self.title_am
        return self.title_en

    def get_description(self, is_amharic=False):
        if is_amharic and self.description_am:
            return self.description_am
        return self.description_en


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

    def get_title(self, is_amharic=False):
        if is_amharic and self.title_am:
            return self.title_am
        return self.title_en

    def get_lyrics(self, is_amharic=False):
        if is_amharic and self.lyrics_am:
            return self.lyrics_am
        return self.lyrics_en

    @property
    def youtube_embed_id(self):
        if not self.youtube_url:
            return None
        # Extract YouTube ID from various URL patterns
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(pattern, self.youtube_url)
        return match.group(1) if match else None