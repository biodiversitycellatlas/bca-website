from django.urls import path
from django.contrib import admin

from . import views

admin.site.site_header = 'BCA Data Portal'
admin.site.site_title = 'BCA Data Portal admin'

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("atlas/", views.AtlasView.as_view(), name="atlas"),
    path("atlas/<dataset>/", views.AtlasInfoView.as_view(), name="atlas_info"),
    path("atlas/<dataset>/overview/", views.AtlasOverviewView.as_view(), name="atlas_overview"),
    path("atlas/<dataset>/gene/", views.AtlasGeneView.as_view(), name="atlas_gene"),
    path("atlas/<dataset>/gene/<gene>", views.AtlasGeneView.as_view(), name="atlas_gene"),
    path("atlas/<dataset>/panel/", views.AtlasPanelView.as_view(), name="atlas_panel"),
    path("atlas/<dataset>/markers/", views.AtlasMarkersView.as_view(), name="atlas_markers"),
    path("atlas/<dataset>/compare/", views.AtlasCompareView.as_view(), name="atlas_compare"),

    path("downloads/", views.DownloadsView.as_view(), name="downloads"),
    path('downloads/<slug:slug>', views.FileDownloadView.as_view(), name='download_file'),

    path("about/", views.AboutView.as_view(), name="about"),
    path("search/", views.SearchView.as_view(), name="search"),
]
