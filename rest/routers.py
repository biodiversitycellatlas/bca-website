from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'species', views.SpeciesViewSet)
router.register(r'gene', views.GeneViewSet)
router.register(r'metacell', views.MetacellViewSet)
router.register(r'metacellgeneexpression', views.MetacellGeneExpressionViewSet)
