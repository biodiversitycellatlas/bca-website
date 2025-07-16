from django.conf import settings


def global_settings(request):
    # Make settings (including GLOBAL VARIABLES) accessible in Django templates
    return {
        key: getattr(settings, key) for key in dir(settings) if not key.startswith("_")
    }
