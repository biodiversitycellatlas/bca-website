from django.urls import path
from django.contrib import admin

from . import views

admin.site.site_header = 'BCA website'
admin.site.site_title = 'BCA website admin'

urlpatterns = [
    path("", views.index, name="index"),
    path("atlas", views.atlas, name="atlas"),
    path("markers", views.markers, name="markers"),
    path("comparison", views.comparison, name="comparison"),
    path("downloads", views.downloads, name="downloads"),
    path("blog", views.blog, name="blog"),
    path("about", views.about, name="about"),
]
