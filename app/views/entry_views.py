from django.views.generic import DetailView, ListView, TemplateView

from ..models import Dataset, Domain, Gene, GeneList, GeneModule, Ortholog, Species
from ..utils import get_dataset, get_gene_list, get_species


class EntryView(TemplateView):
    template_name = "app/entries/entry.html"


class SpeciesListView(ListView):
    model = Species
    paginate_by = 20
    template_name = "app/entries/species_list.html"


class SpeciesDetailView(DetailView):
    model = Species
    template_name = "app/entries/species_detail.html"
    slug_field = "scientific_name"
    slug_url_kwarg = "species"


class DatasetListView(ListView):
    model = Dataset
    paginate_by = 20
    template_name = "app/entries/dataset_list.html"


class FilteredListView(ListView):
    """Allow filtering view by dataset or species."""

    filter_by = "dataset"

    def get_filter_function(self):
        if self.filter_by == "dataset":
            return get_dataset
        elif self.filter_by == "species":
            return get_species
        return None

    def get_queryset(self):
        qs = super().get_queryset()
        value = self.kwargs.get(self.filter_by)
        func = self.get_filter_function()
        if value and func:
            obj = func(value)
            qs = qs.filter(**{self.filter_by: obj})
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        value = self.kwargs.get(self.filter_by)
        func = self.get_filter_function()
        if value and func:
            context[self.filter_by] = func(value)
        return context


class GeneListView(FilteredListView):
    model = Gene
    paginate_by = 20
    template_name = "app/entries/gene_list.html"
    filter_by = "species"


class GeneDetailView(DetailView):
    model = Gene
    template_name = "app/entries/gene_detail.html"
    slug_field = "name"
    slug_url_kwarg = "gene"


class GeneListListView(FilteredListView):
    model = GeneList
    paginate_by = 20
    template_name = "app/entries/gene_list_list.html"
    filter_by = "species"


class GeneListDetailView(FilteredListView):
    model = Gene
    paginate_by = 20
    template_name = "app/entries/gene_list_detail.html"
    filter_by = "species"

    def get_queryset(self):
        qs = super().get_queryset()
        gene_list = self.kwargs.get("gene_list")
        return qs.filter(genelists=get_gene_list(gene_list))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gene_list"] = get_gene_list(self.kwargs.get("gene_list"))
        return context


class DomainListView(FilteredListView):
    model = Domain
    paginate_by = 20
    template_name = "app/entries/domain_list.html"
    filter_by = "species"


class DomainDetailView(FilteredListView):
    model = Gene
    paginate_by = 20
    template_name = "app/entries/domain_detail.html"
    filter_by = "species"

    def get_queryset(self):
        qs = super().get_queryset()
        domain = self.kwargs.get("domain")
        return qs.filter(domains__name=domain)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["domain"] = self.kwargs.get("domain")
        return context


class GeneModuleListView(FilteredListView):
    model = GeneModule
    paginate_by = 20
    template_name = "app/entries/gene_module_list.html"

    def get_queryset(self):
        return super().get_queryset().distinct("dataset", "name")


class GeneModuleDetailView(FilteredListView):
    model = GeneModule
    paginate_by = 20
    template_name = "app/entries/gene_module_detail.html"

    def get_queryset(self):
        qs = super().get_queryset()
        module = self.kwargs.get("gene_module")
        dataset = get_dataset(self.kwargs.get("dataset"))
        return qs.filter(name=module, dataset=dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["module"] = self.kwargs.get("gene_module")
        context["dataset"] = get_dataset(self.kwargs.get("dataset"))
        return context


class OrthogroupListView(ListView):
    model = Ortholog
    paginate_by = 20
    template_name = "app/entries/orthogroup_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by("orthogroup").distinct("orthogroup")


class OrthogroupDetailView(ListView):
    model = Ortholog
    paginate_by = 20
    template_name = "app/entries/orthogroup_detail.html"

    def get_queryset(self):
        qs = super().get_queryset()
        orthogroup = self.kwargs.get("orthogroup")
        return qs.filter(orthogroup=orthogroup)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["orthogroup"] = self.kwargs.get("orthogroup")
        return context
