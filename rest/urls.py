from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from rest.routers import router

from .schema import SpectacularElementsView

app_name = "rest"

urlpatterns = [
    path("", SpectacularElementsView.as_view(url_name="rest:schema"), name="index"),
    path("", include(router.urls), name="rest"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    # path('swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
