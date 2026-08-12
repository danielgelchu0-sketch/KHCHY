from django.contrib import admin
from .models import Album, Song


class SongInline(admin.TabularInline):
    model = Song
    extra = 1
    fields = ('track_number', 'title_en', 'title_am', 'audio_file', 'youtube_url')


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('title_en', 'title_am', 'release_year', 'created_at')
    search_fields = ('title_en', 'title_am')
    inlines = [SongInline]


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title_en', 'album', 'track_number')
    list_filter = ('album',)
    search_fields = ('title_en', 'title_am', 'lyrics_en', 'lyrics_am')