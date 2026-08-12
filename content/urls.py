from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    path('events/', views.event_list, name='event_list'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
]