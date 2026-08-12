from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls', namespace='core')),
    path('music/', include('music.urls', namespace='music')),
    path('content/', include('content.urls', namespace='content')),
    path('rehearsal/', include('rehearsal.urls', namespace='rehearsal')),
]


# Serve media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)