from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
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


def set_language(request):
    lang = request.GET.get('lang', 'en')
    if lang not in ['en', 'am']:
        lang = 'en'

    request.session['django_language'] = lang

    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or '/'
    if not url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}):
        next_url = '/'

    response = redirect(next_url)
    response.set_cookie('django_language', lang, max_age=365 * 24 * 60 * 60, samesite='Lax')
    return response