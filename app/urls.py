from django.urls import path

from . import views

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
    path("entry/species/", views.EntrySpeciesListView.as_view(), name="species_entry"),
    path(
        "entry/species/<str:species>/",
        views.EntrySpeciesDetailView.as_view(),
        name="species_entry",
    ),
    path("entry/dataset/", views.EntryDatasetListView.as_view(), name="dataset_entry"),
    path("entry/gene/", views.EntryGeneListView.as_view(), name="gene_entry"),
    path(
        "entry/gene/<str:species>/",
        views.EntryGeneListView.as_view(),
        name="gene_entry",
    ),
    path(
        "entry/gene/<str:species>/<str:gene>/",
        views.EntryGeneDetailView.as_view(),
        name="gene_entry",
    ),
    path(
        "entry/gene-list/",
        views.EntryGeneListListView.as_view(),
        name="gene_list_entry",
    ),
    path(
        "entry/gene-list/<str:gene_list>/",
        views.EntryGeneListDetailView.as_view(),
        name="gene_list_entry",
    ),
    path(
        "entry/gene-list/<str:gene_list>/<str:species>/",
        views.EntryGeneListDetailView.as_view(),
        name="gene_list_entry",
    ),
    path("entry/domain/", views.EntryDomainListView.as_view(), name="domain_entry"),
    path(
        "entry/domain/<str:domain>/",
        views.EntryDomainDetailView.as_view(),
        name="domain_entry",
    ),
    path(
        "entry/domain/<str:domain>/<str:species>/",
        views.EntryDomainDetailView.as_view(),
        name="domain_entry",
    ),
    path(
        "entry/gene-module/",
        views.EntryGeneModuleListView.as_view(),
        name="gene_module_entry",
    ),
    path(
        "entry/gene-module/<str:dataset>/",
        views.EntryGeneModuleListView.as_view(),
        name="gene_module_entry",
    ),
    path(
        "entry/gene-module/<str:dataset>/<str:gene_module>/",
        views.EntryGeneModuleDetailView.as_view(),
        name="gene_module_entry",
    ),
    path(
        "entry/orthogroup/",
        views.EntryOrthogroupListView.as_view(),
        name="orthogroup_entry",
    ),
    path(
        "entry/orthogroup/<str:orthogroup>/",
        views.EntryOrthogroupDetailView.as_view(),
        name="orthogroup_entry",
    ),

    # Other paths
    path("downloads/", views.DownloadsView.as_view(), name="downloads"),
    path(
        "downloads/<slug:slug>/", views.FileDownloadView.as_view(), name="download_file"
    ),
    path("about/", views.AboutView.as_view(), name="about"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("health/", views.HealthView.as_view(), name="health"),

    # Error pages
    path("403/", views.Custom403View.as_view()),
    path("404/", views.Custom404View.as_view()),
    path("500/", views.Custom500View.as_view()),
]
