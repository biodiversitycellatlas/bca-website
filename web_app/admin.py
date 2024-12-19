from django.contrib import admin
from django.template.defaultfilters import truncatechars

from . import models


class MetaInline(admin.TabularInline):
    model = models.Meta
    extra = 3


class SpeciesAdmin(admin.ModelAdmin):
    list_display = ["scientific_name", "common_name"]
    search_fields = list_display
    inlines = [MetaInline]


class SingleCellAdmin(admin.ModelAdmin):
    list_display = ["id", "x", "y", "metacell", "metacell__type", "species"]
    list_filter = ["species", "metacell__type"]


class MetacellAdmin(admin.ModelAdmin):
    list_display = ["name", "x", "y", "type__name", "type__color", "species"]
    list_filter = ["species", "type"]


class MetacellTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "species"]
    list_filter = ["species"]


class MetacellLinkAdmin(admin.ModelAdmin):
    list_display = ["id", "metacell", "metacell__type", "metacell2", "metacell2__type", "species"]
    list_filter = ["species"]


class GeneAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "domains", "species"]
    search_fields = ["name", "description"] 
    list_filter = ["species"]


class MetacellGeneExpressionAdmin(admin.ModelAdmin):
    list_display = ["gene", "metacell", "fold_change", "umifrac", "species"]
    list_filter = ["species"]


class OrthologAdmin(admin.ModelAdmin):
    list_select_related = ["species", "gene"]
    list_display = ["orthogroup", "gene", "species"]
    search_fields = ["orthogroup", "gene"]
    list_filter = ["species"]


admin.site.register(models.Species, SpeciesAdmin)

admin.site.register(models.SingleCell, SingleCellAdmin)
admin.site.register(models.Metacell, MetacellAdmin)
admin.site.register(models.MetacellType, MetacellTypeAdmin)
admin.site.register(models.MetacellLink, MetacellLinkAdmin)

admin.site.register(models.Gene, GeneAdmin)
admin.site.register(models.MetacellGeneExpression, MetacellGeneExpressionAdmin)
admin.site.register(models.Ortholog, OrthologAdmin)
