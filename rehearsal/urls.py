from django.urls import path
from . import views

app_name = 'rehearsal'

urlpatterns = [
    path('', views.rehearsal_list, name='rehearsal_list'),
    path('<int:pk>/', views.rehearsal_detail, name='rehearsal_detail'),
]