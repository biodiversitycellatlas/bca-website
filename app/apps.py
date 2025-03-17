from django.apps import AppConfig
from django.db.models.signals import post_migrate
import logging

logger = logging.getLogger(__name__)

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    verbose_name = 'BCA data'

    def ready(self):
        post_migrate.connect(self.create_materialized_views, sender=self)

    def create_materialized_views(self, **kwargs):
        """ Runs after migration to create all materialized views """
        logger.warning('\nCreating materialized views...')

        # Fetch all models that are based on MaterialedModel
        from . import models
        materialized = models.MaterializedModel

        for name, model in models.__dict__.items():
            if (
                isinstance(model, type) and
                issubclass(model, materialized) and
                model is not materialized
            ):
                model.create()

        logger.warning('All materialized views created.\n')
