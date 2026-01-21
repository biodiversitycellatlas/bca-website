"""
Global URL configuration.
"""

from django.conf import settings
from django.shortcuts import redirect
from django.urls import include, path, reverse

urlpatterns = [
    path("", include("app.urls")),
    path("api/v1/", include("rest.urls")),
    path("api/", lambda request: redirect(reverse("rest:index"), permanent=False), name="api"),
    path("", include("django_prometheus.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
