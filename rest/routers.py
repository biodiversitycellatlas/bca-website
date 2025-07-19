from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register("species", views.SpeciesViewSet)
router.register("datasets", views.DatasetViewSet)
router.register("stats", views.StatsViewSet, basename="stats")

router.register("genes", views.GeneViewSet)

router.register("gene_lists", views.GeneListViewSet)
router.register("domains", views.DomainViewSet)
router.register("correlated", views.CorrelatedGenesViewSet, basename="correlated")

router.register("orthologs", views.OrthologViewSet)
router.register("ortholog_counts", views.OrthologCountViewSet, basename="orthologcount")
router.register("samap", views.SAMapViewSet)

router.register("metacells", views.MetacellViewSet)
router.register("metacell_links", views.MetacellLinkViewSet, basename="metacelllink")
router.register("metacell_expression", views.MetacellGeneExpressionViewSet)
router.register("markers", views.MetacellMarkerViewSet, basename="metacellmarker")
router.register("metacell_counts", views.MetacellCountViewSet, basename="metacellcount")

router.register("single_cells", views.SingleCellViewSet)
router.register("single_cell_expression", views.SingleCellGeneExpressionViewSet)

router.register("align", views.AlignViewSet, basename="align")
