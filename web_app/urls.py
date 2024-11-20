from django.urls import path
from django.contrib import admin

from . import views

admin.site.site_header = 'BCA website'
admin.site.site_title = 'BCA website admin'

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("atlas/", views.atlas, name="atlas"),
    path("atlas/<species>", views.atlas_info, name="atlas-info"),
    path("atlas/<species>/overview", views.atlas_overview, name="atlas-overview"),
    path("atlas/<species>/markers", views.atlas_markers, name="atlas-markers"),

    path("comparison/", views.ComparisonView.as_view(), name="comparison"),
    path("downloads/", views.DownloadsView.as_view(), name="downloads"),
    path("blog/", views.BlogView.as_view(), name="blog"),
    path("about/", views.AboutView.as_view(), name="about"),
]
