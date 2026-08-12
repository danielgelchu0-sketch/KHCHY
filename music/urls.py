from django.urls import path
from . import views

app_name = 'music'

urlpatterns = [
    path('albums/', views.album_list, name='album_list'),
    path('albums/<int:pk>/', views.album_detail, name='album_detail'),
]