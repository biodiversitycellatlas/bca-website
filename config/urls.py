from django.urls import include, path, reverse
from django.shortcuts import redirect

urlpatterns = [
    path("", include("app.urls")),
    path("api/v1/", include("rest.urls")),
    path(
        "api/",
        lambda request: redirect(reverse("rest:index"), permanent=False),
        name="api",
    ),
]
