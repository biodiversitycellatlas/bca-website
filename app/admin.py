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


class FileAdmin(admin.ModelAdmin):
    list_display = ["type", "species", "file", "checksum"]
    list_filter = ["species"]


class SingleCellAdmin(admin.ModelAdmin):
    list_display = ["name", "metacell", "metacell__type", "dataset"]
    list_filter = ["dataset", "metacell__type"]


class MetacellAdmin(admin.ModelAdmin):
    list_display = ["name", "type__name", "type__color"]
    list_filter = ["dataset", "type"]


class MetacellTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "dataset"]
    list_filter = ["dataset"]


class GeneAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "species", "genelist_names"]
    search_fields = ["name", "description"]
    list_filter = ["species", "genelists"]
    filter_horizontal = ('genelists',)


class GeneListAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name", "description"]


class MetacellGeneExpressionAdmin(admin.ModelAdmin):
    list_display = ["id", "gene", "metacell", "fold_change", "umifrac", "dataset"]
    list_filter = ["dataset"]


class SingleCellGeneExpressionAdmin(admin.ModelAdmin):
    list_display = ["id", "gene", "single_cell", "umi_raw", "dataset"]
    list_filter = ["dataset"]


class OrthologAdmin(admin.ModelAdmin):
    list_select_related = ["species", "gene"]
    list_display = ["orthogroup", "gene", "species"]
    search_fields = ["orthogroup", "gene"]
    list_filter = ["species"]


admin.site.register(models.Species, SpeciesAdmin)
admin.site.register(models.File, FileAdmin)

admin.site.register(models.SingleCell, SingleCellAdmin)
admin.site.register(models.Metacell, MetacellAdmin)
admin.site.register(models.MetacellType, MetacellTypeAdmin)

admin.site.register(models.Gene, GeneAdmin)
admin.site.register(models.GeneList, GeneListAdmin)

admin.site.register(models.MetacellGeneExpression, MetacellGeneExpressionAdmin)
admin.site.register(models.SingleCellGeneExpression, SingleCellGeneExpressionAdmin)
admin.site.register(models.Ortholog, OrthologAdmin)
