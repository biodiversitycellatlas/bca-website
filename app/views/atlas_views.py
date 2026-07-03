"""
Views for Cell Atlas pages, handling dataset-specific info, gene details,
panels, markers, comparisons, and main atlas landing.
"""

import random

from django.db.models import F, Q
from django.shortcuts import redirect, reverse
from django.views.generic import TemplateView

from ..models import Dataset
from ..utils import (
    get_dataset,
    get_dataset_dict,
    get_metacell_dict,
)


class BaseAtlasView(TemplateView):
    """
    Base view for dataset-specific Cell Atlas pages.

    Redirects to standard Atlas view with a warning for invalid datasets.
    """

    model = Dataset
    template_name = "app/atlas/info.html"

    def get_cell_atlas_links(self, url_name, dataset=None):
        """Return links to Cell Atlas navigation bar."""

        links = [
            {
                "name": "Information",
                "icon": "dna",
                "url_view": "atlas_info",
            },
            {
                "name": "Atlas overview",
                "icon": "diagram-project",
                "url_view": "atlas_overview",
            },
            {
                "name": "Gene lists",
                "icon": "solar-panel",
                "url_view": "atlas_panel",
            },
            {
                "name": "Gene modules",
                "icon": "puzzle-piece",
                "url_view": "atlas_modules",
            },
            {
                "name": "Gene and orthologs",
                "icon": "bezier-curve",
                "url_view": "atlas_gene",
                "tooltip": "Visualise gene and ortholog expression",
            },
            {
                "name": "Cell type markers",
                "icon": "list-ol",
                "url_view": "atlas_markers",
                "tooltip": "Identify genes with specific expression patterns in selected metacells",
            },
            {
                "name": "Cell type hierarchy",
                "icon": "sitemap",
                "url_view": "atlas_hierarchy",
            },
            {
                "name": "Cross-species",
                "icon": "scale-unbalanced",
                "url_view": "atlas_compare",
                "tooltip": "Compare genes between cell types of different species",
            },
        ]

        for link in links:
            link["disabled"] = dataset is None
            link["active"] = url_name == link.get("url_view")
            if link["active"]:
                link["href"] = "#top"
            elif dataset is not None:
                d = get_dataset(dataset)
                if isinstance(d, Dataset):
                    link["href"] = reverse(link["url_view"], args=[d.slug])
                else:
                    link["href"] = reverse("atlas")
            else:
                link["href"] = "#"
        return links

    def get_context_data(self, **kwargs):
        """Add dataset, species, links, and query to context."""
        context = super().get_context_data(**kwargs)

        # Get URL query parameters
        query = self.request.GET
        context["query"] = query
        context["dataset_dict"] = get_dataset_dict()

        dataset = context.get("dataset")
        context["dataset"] = dataset

        if dataset is not None:
            d = get_dataset(dataset)
            if isinstance(d, Dataset):
                context["dataset"] = d
                context["species"] = d.species

        # Prepare Cell Atlas links
        url_name = self.request.resolver_match.url_name
        context["links"] = self.get_cell_atlas_links(url_name, context["dataset"])

        return context

    def get(self, *args, **kwargs):
        """Proceed normally unless dataset is invalid."""
        context = self.get_context_data(**kwargs)
        dataset = context.get("dataset")

        if dataset is None or isinstance(dataset, Dataset):
            return super().get(*args, **kwargs)
        else:
            return redirect(reverse("atlas") + "?dataset=" + dataset)


class AtlasView(BaseAtlasView):
    """Main Atlas page with random species icon and dataset selection."""

    template_name = "app/atlas/atlas.html"

    def get_species_icon(self, species=None):
        """Get species icon name, randomly chosen if not provided."""
        if species is None:
            species = [
                "frog",
                "mosquito",
                "cow",
                "otter",
                "kiwi-bird",
                "shrimp",
                "crow",
                "dove",
                "fish-fins",
                "cat",
                "locust",
                "tree",
                "spider",
                "hippo",
            ]
            species = random.choice(species)
        return species

    def get_context_data(self, **kwargs):
        """Add icon, dataset info, warnings, and links to context."""
        context = super().get_context_data(**kwargs)
        context["icon"] = self.get_species_icon()

        query = self.request.GET
        if query and query.get("dataset"):
            dataset = get_dataset(query["dataset"])
            if isinstance(dataset, Dataset):
                context["dataset"] = dataset
            else:
                # Warn that dataset is not available in the database
                context["warning"] = {
                    "title": f"Invalid dataset <code>{query['dataset']}</code>!",
                    "description": "Please check available datasets in the search box above.",
                }

        return context

    def get(self, request, *args, **kwargs):
        """Redirect to dataset-specific atlas page if dataset is provided."""

        query = self.request.GET
        dataset = request.COOKIES.get("dataset") or query.get("dataset")

        if dataset is not None:
            dataset = get_dataset(dataset)

        if dataset and isinstance(dataset, Dataset):
            return redirect("atlas_info", dataset.slug)
        return super().get(request, *args, **kwargs)


class AtlasInfoView(BaseAtlasView):
    """Dataset info page."""

    template_name = "app/atlas/info.html"

    def get_context_data(self, **kwargs):
        """Add quality control metrics."""

        context = super().get_context_data(**kwargs)
        dataset = context.get("dataset")
        qc_values = dataset.qc.annotate(name=F("metric__name"), description=F("metric__description")).values(
            "name", "description", "value"
        )

        qc_metrics = [
            {
                "title": "Mapping metrics",
                "img_url": "https://images.unsplash.com/photo-1663895064411-fff0ab8a9797",
                "img_author": "Javier Miranda",
                "img_author_handle": "nuvaproductions",
            },
            {
                "title": "Quality metrics",
                "img_url": "https://images.unsplash.com/photo-1535127022272-dbe7ee35cf33",
                "img_author": "Michael Schiffer",
                "img_author_handle": "michael_schiffer_design",
            },
            {
                "title": "Cell metrics",
                "img_url": "https://images.unsplash.com/photo-1631556097152-c39479bbff93",
                "img_author": "National Cancer Institute",
                "img_author_handle": "nci",
            },
        ]

        for each in qc_metrics:
            each["values"] = qc_values.filter(metric__type=each["title"])
        context["qc_metrics"] = qc_metrics

        return context


class AtlasOverviewView(BaseAtlasView):
    """Cell Atlas overview page."""

    template_name = "app/atlas/overview.html"

    def get_context_data(self, **kwargs):
        """Add metacell dictionary if dataset is valid."""
        context = super().get_context_data(**kwargs)
        dataset = context.get("dataset")
        context["metacell_dict"] = get_metacell_dict(dataset)
        return context


class AtlasGeneView(BaseAtlasView):
    """Gene detail page within a specific dataset."""

    template_name = "app/atlas/gene.html"

    def get_context_data(self, **kwargs):
        """Add gene info or warning if gene invalid."""
        context = super().get_context_data(**kwargs)

        gene = context.get("gene")
        if gene:
            # Fetch information on selected gene
            obj = dataset.species.genes.filter(name=gene)
            if obj:
                context["gene"] = obj.first()
            else:
                # Throw a warning if gene does not exist
                context["gene"] = ""
                context["warning"] = {
                    "title": f"Invalid gene <code>{gene}</code>!",
                    "description": "Please check available genes in the search box above.",
                }
        return context


class AtlasGeneModuleView(BaseAtlasView):
    """Gene modules page for a specific dataset."""

    template_name = "app/atlas/modules.html"


class AtlasPanelView(BaseAtlasView):
    """Gene panel page for selected metacells."""

    template_name = "app/atlas/panel.html"

    def get_context_data(self, **kwargs):
        """Add metacell dictionary if dataset valid."""
        context = super().get_context_data(**kwargs)
        dataset = context.get("dataset")
        context["metacell_dict"] = get_metacell_dict(dataset)
        return context


class AtlasCellTypeHierarchyView(BaseAtlasView):
    """Cell type hierarchy page."""

    template_name = "app/atlas/hierarchy.html"


class AtlasMarkersView(BaseAtlasView):
    """Cell type markers page."""

    template_name = "app/atlas/markers.html"

    def get_context_data(self, **kwargs):
        """Add metacell dictionary, selected metacells, or warnings."""
        context = super().get_context_data(**kwargs)
        dataset = context.get("dataset")
        context["metacell_dict"] = get_metacell_dict(dataset)

        # Get URL query parameters and prepare table with cell markers
        query = self.request.GET
        if query:
            context["query"] = query
            if "metacells" in query.keys():
                # get selected metacells
                metacells = query["metacells"].split(",")
                selected = list(
                    dataset.metacells.filter(Q(name__in=metacells) | Q(type__name__in=metacells))
                    .values_list("name", flat=True)
                    .distinct()
                )
                selected = [int(s) for s in selected]
                selected.sort()

                context["metacells"] = selected
            else:
                context["warning"] = {
                    "title": "Invalid URL!",
                    "description": (f"Missing <code>metacells</code> in your query: <code>{query.urlencode()}</code>"),
                }
        return context


class AtlasCompareView(BaseAtlasView):
    """Comparison page between multiple datasets."""

    template_name = "app/atlas/compare.html"

    def get_context_data(self, **kwargs):
        """Add second dataset and species for comparison if valid."""
        context = super().get_context_data(**kwargs)

        # Parse URL query parameters and get dataset to compare SAMap scores
        try:
            query = self.request.GET
            if query["dataset"]:
                dataset2 = get_dataset(query["dataset"])
                context["dataset2"] = dataset2
                context["species"] = dataset2.species
        except (KeyError, TypeError, ValueError):
            pass
        return context
