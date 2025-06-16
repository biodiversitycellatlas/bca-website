from django.db import models, connection
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField
from django.utils.text import slugify

from colorfield.fields import ColorField
import re
import hashlib


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

        regex = r'https?://(?:[a-zA-Z0-9-]+\.)?([a-zA-Z0-9-]+)\.'
        match = re.match(regex, self.image_url)
        if match:
            return match.group(1).capitalize()
        return None


class Species(SlugMixin, ImageSourceMixin):
    common_name     = models.CharField(
        max_length=100, null=True,
        help_text="Common name of the species")
    scientific_name = models.CharField(
        max_length=100, unique=True,
        help_text="Scientific name of the species")
    description     = models.TextField(
        blank=True, null=True, help_text="Species description")
    image_url       = models.URLField(
        blank=True, null=True, help_text="URL for species image")

    class Meta:
        verbose_name = "species"
        verbose_name_plural = verbose_name

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
    species = models.ForeignKey(Species, on_delete=models.CASCADE,
                                related_name="datasets")
    name = models.CharField(
        max_length=255, default=None, null=True, help_text="Name of the dataset")
    description = models.TextField(
        blank=True, null=True, help_text="Description of the dataset")
    image_url = models.URLField(
        blank=True, null=True, help_text="URL for dataset image")
    date_created = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the dataset was created")
    date_updated = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the dataset was last updated")

    source = models.ForeignKey(
        Source, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Source of the dataset")
    #version = models.CharField(max_length=50, blank=True, null=True)
    #is_public = models.BooleanField(default=True)

    # Dataset order: only required if revelant, such as in the case of
    # developmental stages
    order = models.PositiveIntegerField(
        default=0, help_text="Order of the dataset (for ordinal sets like developmental stages)")

    class Meta:
        unique_together = ('species', 'name')

    def __str__(self):
        name = self.species.scientific_name
        if self.name is not None:
            name = f"{name} – {self.name}"
        return name

class File(models.Model):
    title_choices = {
        "Proteome": "Proteome",
        "DIAMOND": "DIAMOND"
    }

    species     = models.ForeignKey(Species, on_delete=models.CASCADE,
                                    related_name="files")
    title       = models.CharField(max_length=255, choices=title_choices)
    file        = models.FileField(upload_to="data/")
    checksum    = models.CharField(max_length=64, editable=False)

    def save(self, *args, **kwargs):
        if self.file:
            hasher = hashlib.sha256()
            for chunk in self.file.chunks():
                hasher.update(chunk)
            self.checksum = hasher.hexdigest()
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ["species", "title"]

    def __str__(self):
        return f"{self.species.scientific_name} - {self.title}"


class Meta(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    key     = models.CharField(max_length=100)
    value   = models.CharField(max_length=100)
    query_term = models.CharField(max_length=100, null=True,
                                  help_text="Term to use in query URL")
    source = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True)

    @property
    def query_url(self):
        url  = self.source.query_url
        term = self.query_term
        if url and term:
            url = url.replace('{{id}}', term)
        else:
            url = None
        return url

    class Meta:
        unique_together = ["species", "key", "value"]
        verbose_name = "meta"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.value} ({self.key}): {self.species}"


class MetacellType(SlugMixin):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='metacell_types')
    name = models.CharField()
    color = ColorField(default='#AAAAAA')

    class Meta:
        unique_together = ["dataset", "name"]

    def __str__(self):
        return self.name


class MetacellLink(models.Model):
    metacell  = models.ForeignKey('Metacell', related_name='from_links', on_delete=models.CASCADE)
    metacell2 = models.ForeignKey('Metacell', related_name='to_links', on_delete=models.CASCADE)
    dataset   = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='metacell_links')

    def __str__(self):
        return f"{self.metacell} - {self.metacell2}"

class Metacell(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='metacells')
    type = models.ForeignKey(MetacellType, on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=100)
    x = models.FloatField()
    y = models.FloatField()
    links = models.ManyToManyField('self', through='MetacellLink', symmetrical=True)

    class Meta:
        unique_together = ["name", "dataset"]

    def __str__(self):
        return self.name


class MetacellCount(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='metacell_stats')
    metacell = models.ForeignKey(Metacell, on_delete=models.CASCADE, related_name='stats')
    cells = models.IntegerField()
    umis = models.IntegerField()


class SingleCell(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='sc')
    name = models.CharField(max_length=100)
    metacell = models.ForeignKey(Metacell, on_delete=models.SET_NULL, blank=True, null=True)
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
        return Source.objects.get(name='Pfam')

    @property
    def query_term(self):
        return self.name

    @property
    def query_url(self):
        url  = self.source.query_url
        term = self.query_term
        if url and term:
            url = url.replace('{{id}}', term)
        else:
            url = None
        return url

    def __str__(self):
        return str(self.name)


class GeneList(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=400, blank=True, null=True)

    def __str__(self):
        return str(self.name)


class Gene(SlugMixin):
    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name='genes')
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400, blank=True, null=True)
    domains = models.ManyToManyField(Domain)
    genelists = models.ManyToManyField(GeneList)
    correlations = models.ManyToManyField('self', through='GeneCorrelation', symmetrical=True)

    @property
    def orthogroup(self):
        return getattr(self.ortholog_set.first(), 'orthogroup', None)

    def genelist_names(self):
        return [genelist.name for genelist in self.genelists.all()]
    genelist_names.short_description = 'Gene lists'

    class Meta:
        unique_together = ["name", "species"]

    def __str__(self):
        return str(self.name)


class GeneCorrelation(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='gene_corr')
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name='gene')
    gene2 = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name='gene2')

    spearman_rho = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    pearson_r = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)

    class Meta:
        unique_together = ("gene", "gene2")

    def __str__(self):
        return f"{self.gene.name} - {self.gene2.name}"


class MetacellGeneExpression(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='mge')
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name='mge')
    metacell = models.ForeignKey(Metacell, on_delete=models.CASCADE, related_name='mge')
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
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='scge')
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name='scge')
    single_cell = models.ForeignKey(SingleCell, on_delete=models.CASCADE, related_name='scge')
    umi_raw = models.DecimalField(max_digits=8, decimal_places=0, blank=True, null=True)
    umifrac = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)

    class Meta:
        unique_together = ["gene", "single_cell", "dataset"]
        verbose_name = "single-cell gene expression"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.gene} {self.single_cell}"


class Ortholog(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name='orthologs')
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE)
    orthogroup = models.CharField()

    @property
    def expression(self):
        return self.gene.mge.all()

    class Meta:
        unique_together = ["gene", "orthogroup"]
        verbose_name = "single-cell gene expression"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.orthogroup} {self.gene}"

class SAMap(models.Model):
    metacelltype = models.ForeignKey(
        MetacellType, on_delete=models.CASCADE, related_name='samap')
    metacelltype2 = models.ForeignKey(
        MetacellType, on_delete=models.CASCADE, related_name='samap2')
    samap = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ["metacelltype", "metacelltype2"]
        verbose_name = "SAMAP score"

    def __str__(self):
        return f"{self.metacelltype} ({self.metacelltype.dataset}) vs {self.metacelltype2} ({self.metacelltype2.dataset})"
