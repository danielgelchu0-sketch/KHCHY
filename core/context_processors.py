from .models import SiteSetting

def site_settings(request):
    """
    Makes site_settings globally accessible across all templates without passing it
    manually in every render context.
    """
    settings_obj = SiteSetting.objects.first()
    return {
        'site_settings': settings_obj
    }