from django.apps import AppConfig


class RestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rest"

    def ready(self):
        # Register signal receivers that invalidate cached filter choices
        from . import filters  # noqa: F401
