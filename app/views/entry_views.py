"""Views for displaying database entries."""

from django.views.generic import DetailView, ListView, TemplateView

from ..models import Dataset, Domain, Gene, GeneList, GeneModule, Ortholog, Species
from ..utils import get_dataset, get_gene_list, get_species


class EntryView(TemplateView):
    """Landing page for database entries."""
    template_name = "app/entries/entry.html"


class SpeciesListView(ListView):
    """Display paginated list of all species."""
    model = Species
    paginate_by = 20
    template_name = "app/entries/species_list.html"


class SpeciesDetailView(DetailView):
    """Display details for a specific species."""
    model = Species
    template_name = "app/entries/species_detail.html"
    slug_field = "scientific_name"
    slug_url_kwarg = "species"


class DatasetListView(ListView):
    """Display paginated list of all datasets."""
    model = Dataset
    paginate_by = 20
    template_name = "app/entries/dataset_list.html"


class FilteredListView(ListView):
    """Base view for filtering lists by dataset or species."""
    filter_by = "dataset"

    def __get_filter_function(self):
        """Get function to retrieve the appropriate filter."""
        if self.filter_by == "dataset":
            return get_dataset
        if self.filter_by == "species":
            return get_species
        return None

    def get_queryset(self):
        """Get queryset filtered by dataset or species in URL."""
        qs = super().get_queryset()
        value = self.kwargs.get(self.filter_by)
        func = self.__get_filter_function()
        if value and func:
            obj = func(value)
            qs = qs.filter(**{self.filter_by: obj})
        return qs

    def get_context_data(self, **kwargs):
        """Add dataset or species to the context."""
        context = super().get_context_data(**kwargs)
        value = self.kwargs.get(self.filter_by)
        func = self.__get_filter_function()
        if value and func:
            context[self.filter_by] = func(value)
        return context


class GeneListView(FilteredListView):
    """Display genes lists filtered by species."""
    model = Gene
    paginate_by = 20
    template_name = "app/entries/gene_list.html"
    filter_by = "species"


class GeneDetailView(DetailView):
    """Display details for a specific gene."""
    model = Gene
    template_name = "app/entries/gene_detail.html"
    slug_field = "name"
    slug_url_kwarg = "gene"


class GeneListListView(FilteredListView):
    """Display all gene lists for a species."""
    model = GeneList
    paginate_by = 20
    template_name = "app/entries/gene_list_list.html"
    filter_by = "species"


class GeneListDetailView(FilteredListView):
    """Display list of genes in a specific gene list filtered by species."""
    model = Gene
    paginate_by = 20
    template_name = "app/entries/gene_list_detail.html"
    filter_by = "species"

    def get_queryset(self):
        """Filter queryset by gene list."""
        qs = super().get_queryset()
        gene_list = self.kwargs.get("gene_list")
        return qs.filter(genelists=get_gene_list(gene_list))

    def get_context_data(self, **kwargs):
        """Add gene list to context."""
        context = super().get_context_data(**kwargs)
        context["gene_list"] = get_gene_list(self.kwargs.get("gene_list"))
        return context


class DomainListView(FilteredListView):
    """Display a list of domains, optionally filtered by species."""
    model = Domain
    paginate_by = 20
    template_name = "app/entries/domain_list.html"
    filter_by = "species"


class DomainDetailView(FilteredListView):
    """Display list of genes associated with a specific domain and species."""
    model = Gene
    paginate_by = 20
    template_name = "app/entries/domain_detail.html"
    filter_by = "species"

    def get_queryset(self):
        """Filter queryset by domain."""
        qs = super().get_queryset()
        domain = self.kwargs.get("domain")
        return qs.filter(domains__name=domain)

    def get_context_data(self, **kwargs):
        """Add domain to context."""
        context = super().get_context_data(**kwargs)
        context["domain"] = self.kwargs.get("domain")
        return context


class GeneModuleListView(FilteredListView):
    """Display distinct gene modules, optionally filtered by dataset."""
    model = GeneModule
    paginate_by = 20
    template_name = "app/entries/gene_module_list.html"

    def get_queryset(self):
        """Return unique queryset items based on dataset and gene module name."""
        return super().get_queryset().distinct("dataset", "name")


class GeneModuleDetailView(FilteredListView):
    """Display list of genes for a specific gene module and dataset."""
    model = GeneModule
    paginate_by = 20
    template_name = "app/entries/gene_module_detail.html"

    def get_queryset(self):
        """Filter queryset by gene module and dataset."""
        qs = super().get_queryset()
        module = self.kwargs.get("gene_module")
        dataset = get_dataset(self.kwargs.get("dataset"))
        return qs.filter(name=module, dataset=dataset)

    def get_context_data(self, **kwargs):
        """Add module and dataset to context."""
        context = super().get_context_data(**kwargs)
        context["module"] = self.kwargs.get("gene_module")
        context["dataset"] = get_dataset(self.kwargs.get("dataset"))
        return context


class OrthogroupListView(ListView):
    """Display list of unique orthogroups."""
    model = Ortholog
    paginate_by = 20
    template_name = "app/entries/orthogroup_list.html"

    def get_queryset(self):
        """Return distinct orthogroups ordered by name."""
        qs = super().get_queryset()
        return qs.order_by("orthogroup").distinct("orthogroup")


class OrthogroupDetailView(ListView):
    """Display orthologs within a specific orthogroup."""
    model = Ortholog
    paginate_by = 20
    template_name = "app/entries/orthogroup_detail.html"

    def get_queryset(self):
        """Filter queryset by orthogroup."""
        qs = super().get_queryset()
        orthogroup = self.kwargs.get("orthogroup")
        return qs.filter(orthogroup=orthogroup)

    def get_context_data(self, **kwargs):
        """Add orthogroup to context."""
        context = super().get_context_data(**kwargs)
        context["orthogroup"] = self.kwargs.get("orthogroup")
        return context
