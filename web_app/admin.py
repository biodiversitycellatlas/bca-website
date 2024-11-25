from django.contrib import admin
from django.template.defaultfilters import truncatechars

from .models import Species, Meta, SingleCell, Metacell, MetacellLink, Gene, MetacellGeneExpression


class MetaInline(admin.TabularInline):
    model = Meta
    extra = 3


class SpeciesAdmin(admin.ModelAdmin):
    list_display = ["scientific_name", "common_name"]
    search_fields = list_display
    inlines = [MetaInline]


class SingleCellAdmin(admin.ModelAdmin):
    list_display = ["id", "x", "y", "metacell", "metacell__type", "species"]
    list_filter = ["species", "metacell__type"]


class MetacellAdmin(admin.ModelAdmin):
    list_display = ["name", "x", "y", "type", "color", "species"]
    list_filter = ["species", "type"]


class MetacellLinkAdmin(admin.ModelAdmin):
    list_display = ["id", "metacell", "metacell__type", "metacell2", "metacell2__type", "species"]
    list_filter = ["species"]


class GeneAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "domains", "species"]
    search_fields = ["name", "description"] 
    list_filter = ["species"]


class MetacellGeneExpressionAdmin(admin.ModelAdmin):
    list_display = ["gene", "metacell", "value", "species"]


admin.site.register(Species, SpeciesAdmin)

admin.site.register(SingleCell, SingleCellAdmin)
admin.site.register(Metacell, MetacellAdmin)
admin.site.register(MetacellLink, MetacellLinkAdmin)

admin.site.register(Gene, GeneAdmin)
admin.site.register(MetacellGeneExpression, MetacellGeneExpressionAdmin)
