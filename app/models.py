import hashlib
import re
from pathlib import Path

from colorfield.fields import ColorField
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import connection, models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.text import slugify


class SlugMixin(models.Model):
    class Meta:
        abstract = True

    @property
    def slug(self):
        """
        Formats the model representation for safe use in URLs.

        Example:
            For 'Trichoplax adhaerens', returns 'trichoplax-adhaerens'.
        """
        return slugify(str(self))


class ImageSourceMixin(models.Model):
    class Meta:
        abstract = True

    @property
    def image_source(self):
        """
        Extracts the image source domain based on the image URL.

        Example:
            For https://test.wikimedia.org/path/img.jpg, returns Wikimedia.
        """
        if not self.image_url:
            return None

        regex = r"https?://(?:[a-zA-Z0-9-]+\.)?([a-zA-Z0-9-]+)\."
        match = re.match(regex, self.image_url)
        if match:
            return match.group(1).capitalize()
        return None


class Species(SlugMixin, ImageSourceMixin):
    common_name = models.CharField(
        max_length=100, null=True, help_text="Common name of the species"
    )
    scientific_name = models.CharField(
        max_length=100, unique=True, help_text="Scientific name of the species"
    )
    description = models.TextField(
        blank=True, null=True, help_text="Species description"
    )
    image_url = models.URLField(
        blank=True, null=True, help_text="URL for species image"
    )

    @property
    def division(self):
        return self.meta_set.filter(key="division").first().value

    @property
    def kingdom(self):
        return self.meta_set.filter(key="kingdom").first().value

    @property
    def phylum(self):
        return self.meta_set.filter(key="phylum").first().value

    @property
    def proteome(self):
        return self.files.get(type="Proteome")

    def get_absolute_url(self):
        return reverse("species_entry", args=[self.scientific_name])

    def get_gene_list_url(self):
        return reverse("gene_entry", args=[self.slug])

    def get_genemodule_list_url(self):
        return reverse("gene_module_entry", args=[self.slug])

    def get_genelist_list_url(self, genelist):
        return reverse("gene_list_entry", args=[genelist, self.slug])

    def get_domain_list_url(self, domain):
        return reverse("domain_entry", args=[domain, self.slug])

    def get_html(self):
        """Return HTML representation of the species name."""
        unspecified = " sp."
        species = self.scientific_name

        if species.lower().endswith(unspecified):
            genus = species.replace(unspecified, "")
            html = f"<i>{genus}</i>{unspecified}"
        else:
            html = f"<i>{species}</i>"
        return mark_safe(html)

    def get_html_link(self, url=None):
        """Return HTML representation linking to species object."""
        url = self.get_absolute_url() if url is None else url
        image_url = self.image_url
        label = self.get_html()
        html = f"""
            <a class="d-flex align-items-center gap-1" href="{url}">
                <img class="rounded" alt="Image of {self.scientific_name}"
                     width="25px" src="{image_url}">
                {label}
            </a>
        """
        return mark_safe(html)

    def get_genes_html_link(self):
        """Return HTML representation linking to list of genes."""
        url = self.get_gene_list_url()
        return self.get_html_link(url)

    class Meta:
        verbose_name = "species"
        verbose_name_plural = verbose_name
        ordering = ["scientific_name"]

    def __str__(self):
        return self.scientific_name


class Source(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    query_url = models.URLField(blank=True, null=True)
    version = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name


class Dataset(SlugMixin, ImageSourceMixin):
    species = models.ForeignKey(
        Species, on_delete=models.CASCADE, related_name="datasets"
    )
    name = models.CharField(
        max_length=255, default=None, null=True, help_text="Name of the dataset"
    )
    description = models.TextField(
        blank=True, null=True, help_text="Description of the dataset"
    )
    image_url = models.URLField(
        blank=True, null=True, help_text="URL for dataset image"
    )
    date_created = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the dataset was created"
    )
    date_updated = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the dataset was last updated"
    )

    source = models.ForeignKey(
        Source,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Source of the dataset",
    )
    # version = models.CharField(max_length=50, blank=True, null=True)
    # is_public = models.BooleanField(default=True)

    # Dataset order: only required if revelant, such as in the case of
    # developmental stages
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order of the dataset (for ordinal sets like developmental stages)",
    )

    def __label(self, species):
        dataset = self.name
        return f"{species} ({dataset})" if dataset else species

    def get_html(self):
        """Return HTML representation of the dataset."""
        return mark_safe(self.__label(self.species.get_html()))

    def get_html_link(self, url=None):
        """Return HTML representation linking to the Dataset."""
        url = self.get_absolute_url() if url is None else url
        image_url = self.image_url or self.species.image_url
        label = self.get_html()

        html = f'<img width="25px" src="{image_url}"> {label}'
        html = f'<a href="{url}">{html}</a>'
        return mark_safe(html)

    def get_gene_modules_html_link(self):
        """Return HTML representation linking to list of gene modules."""
        url = self.get_gene_module_list_url()
        return self.get_html_link(url)

    def get_absolute_url(self):
        return reverse("atlas_info", args=[str(self.slug)])

    def get_gene_url(self, gene):
        return reverse("atlas_gene", args=[str(self.slug), str(gene)])

    def get_gene_module_list_url(self):
        return reverse("gene_module_entry", args=[self.slug])

    class Meta:
        unique_together = ("species", "name")
        ordering = ["species__scientific_name", "order"]

    def __str__(self):
        return self.__label(self.species.scientific_name)


class File(models.Model):
    file_types = {"Proteome": "Proteome", "DIAMOND": "DIAMOND"}

    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name="files")
    type = models.CharField(max_length=255, choices=file_types)
    file = models.FileField()
    checksum = models.CharField(max_length=64, editable=False)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if self.file:
            hasher = hashlib.sha256()
            for chunk in self.file.chunks():
                hasher.update(chunk)
            self.checksum = hasher.hexdigest()

            if not self.slug:
                base = f"{self.species.scientific_name}-{self.type}"
                self.slug = slugify(base)

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def ext(self):
        return Path(self.file.name).suffix.lstrip(".")

    @property
    def filename(self):
        return f"{self}.{self.ext}"

    class Meta:
        unique_together = ["species", "type"]

    def __str__(self):
        return f"{self.species.scientific_name} - {self.type}"


class Meta(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    query_term = models.CharField(
        max_length=100, null=True, help_text="Term to use in query URL"
    )
    source = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True)

    @property
    def query_url(self):
        url = self.source.query_url
        term = self.query_term
        if url and term:
            url = url.replace("{{id}}", term)
        else:
            url = None
        return url

    def get_absolute_url(self):
        return self.query_url

    @property
    def label(self):
        label = self.key
        if label == "taxon_id":
            label = "Taxon ID"
        else:
            label = label.capitalize()
        return label

    class Meta:
        unique_together = ["species", "key", "value"]
        verbose_name = "meta"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.key.capitalize()}: {self.value}"


class MetacellType(SlugMixin):
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="metacell_types"
    )
    name = models.CharField()
    color = ColorField(default="#AAAAAA")

    class Meta:
        unique_together = ["dataset", "name"]

    def __str__(self):
        return self.name


class MetacellLink(models.Model):
    metacell = models.ForeignKey(
        "Metacell", related_name="from_links", on_delete=models.CASCADE
    )
    metacell2 = models.ForeignKey(
        "Metacell", related_name="to_links", on_delete=models.CASCADE
    )
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="metacell_links"
    )

    def __str__(self):
        return f"{self.metacell} - {self.metacell2}"


class Metacell(models.Model):
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="metacells"
    )
    type = models.ForeignKey(
        MetacellType, on_delete=models.SET_NULL, blank=True, null=True
    )
    name = models.CharField(max_length=100)
    x = models.FloatField()
    y = models.FloatField()
    links = models.ManyToManyField("self", through="MetacellLink", symmetrical=True)

    class Meta:
        unique_together = ["name", "dataset"]

    def __str__(self):
        return self.name


class MetacellCount(models.Model):
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="metacell_stats"
    )
    metacell = models.ForeignKey(
        Metacell, on_delete=models.CASCADE, related_name="stats"
    )
    cells = models.IntegerField()
    umis = models.IntegerField()


class SingleCell(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="sc")
    name = models.CharField(max_length=100)
    metacell = models.ForeignKey(
        Metacell, on_delete=models.SET_NULL, blank=True, null=True
    )
    x = models.FloatField(null=True)
    y = models.FloatField(null=True)

    class Meta:
        unique_together = ["name", "dataset"]

    def __str__(self):
        return self.name


class Domain(models.Model):
    name = models.CharField(max_length=100, unique=True)

    @property
    def source(self):
        return Source.objects.get(name="Pfam")

    @property
    def query_term(self):
        return self.name

    @property
    def query_url(self):
        url = self.source.query_url
        term = self.query_term
        if url and term:
            url = url.replace("{{id}}", term)
        else:
            url = None
        return url

    def get_absolute_url(self):
        return reverse("domain_entry", args=[self.name])

    def get_html_link(self, url=None):
        url = self.get_absolute_url() if url is None else url
        label = self.name

        html = f'<a href="{url}">{label}</a>'
        return mark_safe(html)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return str(self.name)


class GeneList(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=400, blank=True, null=True)

    def get_absolute_url(self):
        return reverse("gene_list_entry", args=[self.name])

    def get_html_link(self, url=None):
        url = self.get_absolute_url() if url is None else url
        label = self.name

        html = f'<a href="{url}">{label}</a>'
        return mark_safe(html)

    def __str__(self):
        return str(self.name)


class Gene(SlugMixin):
    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name="genes")
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400, blank=True, null=True)
    domains = models.ManyToManyField(Domain)
    genelists = models.ManyToManyField(GeneList, related_name="genes")
    correlations = models.ManyToManyField(
        "self", through="GeneCorrelation", symmetrical=True
    )

    @property
    def orthogroup(self):
        return getattr(self.ortholog_set.first(), "orthogroup", None)

    @property
    def slug(self):
        return slugify(f"{self.species.slug}_{str(self)}")

    def genelist_names(self):
        return [genelist.name for genelist in self.genelists.all()]

    genelist_names.short_description = "Gene lists"

    def get_absolute_url(self):
        return reverse("gene_entry", args=[self.species.slug, self.name])

    def get_html_link(self):
        url = self.get_absolute_url()
        label = self.name

        html = f'<a class="text-break" href="{url}">{label}</a>'
        return mark_safe(html)

    def get_orthogroup_html_link(self):
        # Get a ortholog object based on orthogroup
        ortholog = self.ortholog_set.first()
        if ortholog is None:
            return ""

        url = ortholog.get_absolute_url()
        label = ortholog.orthogroup

        html = f'<a href="{url}">{label}</a>'
        return mark_safe(html)

    def get_domain_html_links(self):
        domains = self.domains.all()
        html = ", ".join(d.get_html_link() for d in domains)
        return mark_safe(html)

    class Meta:
        unique_together = ["name", "species"]

    def __str__(self):
        return str(self.name)


class GeneModule(models.Model):
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name="modules")
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="gene_modules"
    )
    name = models.CharField(max_length=100)
    membership_score = models.DecimalField(
        max_digits=4, decimal_places=3, blank=True, null=True
    )

    @property
    def gene_modules(self):
        """Return all gene modules for the same module."""
        return GeneModule.objects.filter(name=self.name, dataset=self.dataset)

    def get_absolute_url(self):
        return reverse("gene_module_entry", args=[self.dataset.slug, self.name])

    def get_html_link(self):
        url = self.get_absolute_url()
        label = self.name

        html = f'<a href="{url}">{label}</a>'
        return mark_safe(html)

    class Meta:
        unique_together = ["gene", "dataset"]

    def __str__(self):
        return str(self.name)


class GeneCorrelation(models.Model):
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="gene_corr"
    )
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name="gene")
    gene2 = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name="gene2")

    spearman = models.DecimalField(
        max_digits=3, decimal_places=2, blank=True, null=True
    )
    pearson = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)

    class Meta:
        unique_together = ("dataset", "gene", "gene2")

    def __str__(self):
        return f"{self.gene.name} - {self.gene2.name}"


class MetacellGeneExpression(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="mge")
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name="mge")
    metacell = models.ForeignKey(Metacell, on_delete=models.CASCADE, related_name="mge")
    umi_raw = models.FloatField(blank=True, null=True)
    umifrac = models.FloatField(blank=True, null=True)
    fold_change = models.FloatField(blank=True, null=True)

    class Meta:
        unique_together = ["gene", "metacell", "dataset"]
        verbose_name = "metacell gene expression"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.gene} {self.metacell}"


class SingleCellGeneExpression(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="scge")
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name="scge")
    single_cell = models.ForeignKey(
        SingleCell, on_delete=models.CASCADE, related_name="scge"
    )
    umi_raw = models.DecimalField(max_digits=8, decimal_places=0, blank=True, null=True)
    umifrac = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)

    class Meta:
        unique_together = ["gene", "single_cell", "dataset"]
        verbose_name = "single-cell gene expression"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.gene} {self.single_cell}"


class Ortholog(models.Model):
    species = models.ForeignKey(
        Species, on_delete=models.CASCADE, related_name="orthologs"
    )
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE)
    orthogroup = models.CharField()

    @property
    def expression(self):
        return self.gene.mge.all()

    @property
    def orthologs(self):
        """Return all ortholog genes for this object's orthogroup."""
        orthogroup = self.orthogroup
        return Ortholog.objects.filter(orthogroup=orthogroup)

    def get_absolute_url(self):
        return reverse("orthogroup_entry", args=[self.orthogroup])

    def get_html_link(self):
        # Get a ortholog object based on orthogroup
        url = self.get_absolute_url()
        label = self.orthogroup

        html = f'<a href="{url}">{label}</a>'
        return mark_safe(html)

    class Meta:
        unique_together = ["gene", "orthogroup"]
        verbose_name = "ortholog"
        ordering = ["species", "gene"]

    def __str__(self):
        return f"{self.orthogroup} {self.gene}"


class SAMap(models.Model):
    metacelltype = models.ForeignKey(
        MetacellType, on_delete=models.CASCADE, related_name="samap"
    )
    metacelltype2 = models.ForeignKey(
        MetacellType, on_delete=models.CASCADE, related_name="samap2"
    )
    samap = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ["metacelltype", "metacelltype2"]
        verbose_name = "SAMAP score"

    def __str__(self):
        return f"{self.metacelltype} ({self.metacelltype.dataset}) vs {self.metacelltype2} ({self.metacelltype2.dataset})"
