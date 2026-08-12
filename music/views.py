from django.shortcuts import render, get_object_or_404
from .models import Album, Song


def album_list(request):
    albums = Album.objects.all()
    return render(request, 'music/album_list.html', {'albums': albums})


def album_detail(request, pk):
    album = get_object_or_404(Album, pk=pk)
    songs = album.songs.all()
    return render(request, 'music/album_detail.html', {'album': album, 'songs': songs})