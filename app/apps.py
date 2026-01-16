import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"
    verbose_name = "BCA data"
