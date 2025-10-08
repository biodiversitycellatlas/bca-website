"""Create sitemaps."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from . import models

class AtlasSitemap(Sitemap):
    """Sitemap for Cell Atlas pages."""
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        """Return list of species to include in the sitemap."""
        return models.Dataset.objects.all()

    def location(self, obj):
        """Return the URL for the main page of a species."""
        return reverse('atlas_info', args=[obj.slug])

    def lastmod(self, obj):
        """
        Return last modified date for the species page.
        Useful to state last update to search engines.
        """
        return obj.date_updated


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages."""
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return ['atlas', 'downloads', 'about', 'entry', 'reference', 'api']

    def location(self, item):
        return reverse(item)