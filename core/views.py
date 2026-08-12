from django.shortcuts import render
from .models import SiteSetting


def home(request):
    site_settings = SiteSetting.objects.first()
    context = {
        'site_settings': site_settings,
    }
    return render(request, 'core/home.html', context)



def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')