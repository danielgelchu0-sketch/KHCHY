from .models import SiteSetting

def site_settings(request):
    """
    Makes site_settings globally accessible across all templates without passing it
    manually in every render context. Also provides current_lang and is_amharic flag.
    """
    lang = request.GET.get('lang')
    if lang in ['en', 'am']:
        if hasattr(request, 'session'):
            request.session['django_language'] = lang
    else:
        if hasattr(request, 'session'):
            lang = request.session.get('django_language')
        if not lang:
            lang = request.COOKIES.get('django_language') or 'en'

    settings_obj = SiteSetting.objects.first()
    is_amharic = (lang == 'am')

    return {
        'site_settings': settings_obj,
        'current_lang': lang,
        'is_amharic': is_amharic,
    }