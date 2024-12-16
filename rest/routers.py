from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'species', views.SpeciesViewSet)
router.register(r'gene', views.GeneViewSet)
router.register(r'single_cell', views.SingleCellViewSet)
router.register(r'metacell', views.MetacellViewSet)
router.register(r'metacell_link', views.MetacellLinkViewSet)
router.register(r'expression', views.MetacellGeneExpressionViewSet)
router.register(r'markers', views.MetacellMarkerViewSet, basename='metacellmarker')
