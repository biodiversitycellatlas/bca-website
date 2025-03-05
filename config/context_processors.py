from django.conf import settings

def global_settings(request):
    settings_list = [
        "DIAMOND_VERSION",
        "MAX_ALIGNMENT_SEQS",
        "MAX_FILE_SIZE"
    ]
    return {key: getattr(settings, key) for key in settings_list}
