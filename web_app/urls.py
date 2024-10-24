from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("atlas", views.atlas, name="atlas"),
    path("markers", views.markers, name="markers"),
    path("comparison", views.comparison, name="comparison"),
    path("downloads", views.downloads, name="downloads"),
    path("blog", views.blog, name="blog"),
    path("about", views.about, name="about"),
]
