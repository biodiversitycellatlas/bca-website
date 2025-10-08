"""
URL routing for the app, including Cell Atlas, database entries,
downloads, search, health check, and custom error pages.
"""

from django.urls import path
from django.contrib.sitemaps.views import sitemap
from .sitemaps import StaticViewSitemap, AtlasSitemap

from . import views

sitemaps = {
    'static': StaticViewSitemap,
    'dataset': AtlasSitemap,
}

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    # Cell Atlas
    path("atlas/", views.AtlasView.as_view(), name="atlas"),
    path("atlas/<str:dataset>/", views.AtlasInfoView.as_view(), name="atlas_info"),
    path(
        "atlas/<str:dataset>/overview/",
        views.AtlasOverviewView.as_view(),
        name="atlas_overview",
    ),
    path("atlas/<str:dataset>/gene/", views.AtlasGeneView.as_view(), name="atlas_gene"),
    path(
        "atlas/<str:dataset>/gene/<str:gene>/",
        views.AtlasGeneView.as_view(),
        name="atlas_gene",
    ),
    path(
        "atlas/<str:dataset>/panel/", views.AtlasPanelView.as_view(), name="atlas_panel"
    ),
    path(
        "atlas/<str:dataset>/markers/",
        views.AtlasMarkersView.as_view(),
        name="atlas_markers",
    ),
    path(
        "atlas/<str:dataset>/compare/",
        views.AtlasCompareView.as_view(),
        name="atlas_compare",
    ),
    # BCA database entries
    path("entry/", views.EntryView.as_view(), name="entry"),
    path("entry/species/", views.SpeciesListView.as_view(), name="species_entry"),
    path(
        "entry/species/<str:species>/",
        views.SpeciesDetailView.as_view(),
        name="species_entry",
    ),
    path("entry/dataset/", views.DatasetListView.as_view(), name="dataset_entry"),
    path("entry/gene/", views.GeneListView.as_view(), name="gene_entry"),
    path(
        "entry/gene/<str:species>/",
        views.GeneListView.as_view(),
        name="gene_entry",
    ),
    path(
        "entry/gene/<str:species>/<str:gene>/",
        views.GeneDetailView.as_view(),
        name="gene_entry",
    ),
    path(
        "entry/gene-list/",
        views.GeneListListView.as_view(),
        name="gene_list_entry",
    ),
    path(
        "entry/gene-list/<str:gene_list>/",
        views.GeneListDetailView.as_view(),
        name="gene_list_entry",
    ),
    path(
        "entry/gene-list/<str:gene_list>/<str:species>/",
        views.GeneListDetailView.as_view(),
        name="gene_list_entry",
    ),
    path("entry/domain/", views.DomainListView.as_view(), name="domain_entry"),
    path(
        "entry/domain/<str:domain>/",
        views.DomainDetailView.as_view(),
        name="domain_entry",
    ),
    path(
        "entry/domain/<str:domain>/<str:species>/",
        views.DomainDetailView.as_view(),
        name="domain_entry",
    ),
    path(
        "entry/gene-module/",
        views.GeneModuleListView.as_view(),
        name="gene_module_entry",
    ),
    path(
        "entry/gene-module/<str:dataset>/",
        views.GeneModuleListView.as_view(),
        name="gene_module_entry",
    ),
    path(
        "entry/gene-module/<str:dataset>/<str:gene_module>/",
        views.GeneModuleDetailView.as_view(),
        name="gene_module_entry",
    ),
    path(
        "entry/orthogroup/",
        views.OrthogroupListView.as_view(),
        name="orthogroup_entry",
    ),
    path(
        "entry/orthogroup/<str:orthogroup>/",
        views.OrthogroupDetailView.as_view(),
        name="orthogroup_entry",
    ),
    # Other paths
    path("downloads/", views.DownloadsView.as_view(), name="downloads"),
    path(
        "downloads/<slug:slug>/", views.FileDownloadView.as_view(), name="download_file"
    ),
    path(
        "reference/", views.ReferenceView.as_view(), {"page": "index"}, name="reference"
    ),
    path("reference/<str:page>/", views.ReferenceView.as_view(), name="reference"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("health/", views.HealthView.as_view(), name="health"),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),

    # Error pages
    path("403/", views.Custom403View.as_view()),
    path("404/", views.Custom404View.as_view()),
    path("500/", views.Custom500View.as_view()),
]
