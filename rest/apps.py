from django.apps import AppConfig


class RestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rest"

    def ready(self):
        # Register signal receivers that invalidate cached filter choices
        from .utils import filters as _filter_utils  # noqa: F401
        from .utils.filters import (
            invalidate_dataset_choices,  # noqa: F401
            invalidate_species_choices,  # noqa: F401
        )
