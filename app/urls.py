from django.urls import path

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),

    # Cell Atlas
    path("atlas/", views.AtlasView.as_view(), name="atlas"),
    path("atlas/<dataset>/", views.AtlasInfoView.as_view(), name="atlas_info"),
    path("atlas/<dataset>/overview/", views.AtlasOverviewView.as_view(), name="atlas_overview"),
    path("atlas/<dataset>/gene/", views.AtlasGeneView.as_view(), name="atlas_gene"),
    path("atlas/<dataset>/gene/<gene>/", views.AtlasGeneView.as_view(), name="atlas_gene"),
    path("atlas/<dataset>/panel/", views.AtlasPanelView.as_view(), name="atlas_panel"),
    path("atlas/<dataset>/markers/", views.AtlasMarkersView.as_view(), name="atlas_markers"),
    path("atlas/<dataset>/compare/", views.AtlasCompareView.as_view(), name="atlas_compare"),

    # BCA database entries
    path('entry/', views.EntryView.as_view(), name='entry'),
    path('entry/species/', views.EntrySpeciesListView.as_view(), name='species_entry'),
    path('entry/species/<species>/', views.EntrySpeciesDetailView.as_view(), name='species_entry'),
    path('entry/dataset/', views.EntryDatasetListView.as_view(), name='dataset_entry'),

    path('entry/gene/', views.EntryGeneListView.as_view(), name='gene_entry'),
    path('entry/gene/<species>/', views.EntryGeneListView.as_view(), name='gene_entry'),
    path('entry/gene/<species>/<gene>/', views.EntryGeneDetailView.as_view(), name='gene_entry'),

    path('entry/gene_list/', views.EntryGeneListListView.as_view(), name='gene_list_entry'),
    path('entry/gene_list/<gene_list>/', views.EntryGeneListDetailView.as_view(), name='gene_list_entry'),
    path('entry/gene_list/<gene_list>/<species>/', views.EntryGeneListDetailView.as_view(), name='gene_list_entry'),

    path('entry/domain/', views.EntryDomainListView.as_view(), name='domain_entry'),
    path('entry/domain/<domain>/', views.EntryDomainDetailView.as_view(), name='domain_entry'),
    path('entry/domain/<domain>/<species>/', views.EntryDomainDetailView.as_view(), name='domain_entry'),

    path('entry/gene_modules/', views.EntryGeneModuleListView.as_view(), name='gene_module_entry'),
    path('entry/gene_modules/<dataset>/', views.EntryGeneModuleListView.as_view(), name='gene_module_entry'),
    path('entry/gene_modules/<dataset>/<gene_module>/', views.EntryGeneModuleDetailView.as_view(), name='gene_module_entry'),

    path('entry/orthogroup/', views.EntryOrthogroupListView.as_view(), name='orthogroup_entry'),
    path('entry/orthogroup/<orthogroup>/', views.EntryOrthogroupDetailView.as_view(), name='orthogroup_entry'),

    # Remaining paths
    path("downloads/", views.DownloadsView.as_view(), name="downloads"),
    path('downloads/<slug:slug>/', views.FileDownloadView.as_view(), name='download_file'),
    path("about/", views.AboutView.as_view(), name="about"),
    path("search/", views.SearchView.as_view(), name="search"),
]
