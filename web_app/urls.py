from django.urls import path
from django.contrib import admin

from . import views

admin.site.site_header = 'BCA website'
admin.site.site_title = 'BCA website admin'

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("atlas/", views.AtlasView.as_view(), name="atlas"),
    path("atlas/<species>/", views.AtlasInfoView.as_view(), name="atlas_info"),
    path("atlas/<species>/overview/", views.AtlasOverviewView.as_view(), name="atlas_overview"),
    path("atlas/<species>/markers/", views.AtlasMarkersView.as_view(), name="atlas_markers"),

    path("comparison/", views.ComparisonView.as_view(), name="comparison"),
    path("downloads/", views.DownloadsView.as_view(), name="downloads"),
    path("blog/", views.BlogView.as_view(), name="blog"),
    path("about/", views.AboutView.as_view(), name="about"),
]
