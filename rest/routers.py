from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register('species', views.SpeciesViewSet)

router.register('gene', views.GeneViewSet)
router.register('gene_lists', views.GeneListViewSet)
router.register('orthologs', views.OrthologViewSet)

router.register('metacell', views.MetacellViewSet)
router.register('metacell_link', views.MetacellLinkViewSet)
router.register('metacell_expression', views.MetacellGeneExpressionViewSet)
router.register('markers', views.MetacellMarkerViewSet, basename='metacellmarker')

router.register('single_cell', views.SingleCellViewSet)
router.register('single_cell_expression', views.SingleCellGeneExpressionViewSet)

router.register('align', views.AlignViewSet, basename='align')
