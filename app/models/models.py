from django.db import models, connection
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField
from django.utils.text import slugify

from colorfield.fields import ColorField
import re
import hashlib


class Species(models.Model):
    common_name     = models.CharField(
        max_length=100, unique=True, help_text="Common name used for the species")
    scientific_name = models.CharField(
        max_length=100, unique=True, help_text="Scientific name used for the species")
    description     = models.TextField(
        blank=True, null=True, help_text="Species description")
    image_url       = models.URLField(
        blank=True, null=True, help_text="URL for species image")

    @property
    def slug(self):
        """
        Formats the model representation for safe use in URLs.

        Example:
            For 'Trichoplax adhaerens', returns 'trichoplax-adhaerens'.
        """
        return slugify(self)

    @property
    def image_source(self):
        """
        Get image source based on the domain of the image URL.

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

    class Meta:
        verbose_name = "species"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.scientific_name


class Source(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    version = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name


class Dataset(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE,
                                related_name="datasets")
    name = models.CharField(
        max_length=255, default=None, null=True, help_text="Name of the dataset")
    description = models.TextField(
        blank=True, null=True, help_text="Description of the dataset")
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

    @property
    def slug(self):
        """
        Formats the model representation for safe use in URLs.

        Example:
            For an adult mouse dataset, returns 'mus-musculus-adult'.
        """
        return slugify(self)

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

    class Meta:
        unique_together = ["species", "key", "value"]
        verbose_name = "meta"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.value} ({self.key}): {self.species}"


class MetacellType(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='metacell_types')
    name = models.CharField()
    color = ColorField(default='#AAAAAA')

    @property
    def slug(self):
        """
        Formats the model representation for safe use in URLs.

        Example:
            For 'Epithelial cells', returns 'epithelial-cells'.
        """
        return slugify(self)

    class Meta:
        unique_together = ["dataset", "name"]

    def __str__(self):
        return self.name


class MetacellLink(models.Model):
    metacell  = models.ForeignKey('Metacell', related_name='from_links', on_delete=models.CASCADE)
    metacell2 = models.ForeignKey('Metacell', related_name='to_links', on_delete=models.CASCADE)

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


class SingleCell(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='sc')
    name = models.CharField(max_length=100)
    metacell = models.ForeignKey(Metacell, on_delete=models.SET_NULL, blank=True, null=True)
    x = models.FloatField()
    y = models.FloatField()

    class Meta:
        unique_together = ["name", "dataset"]

    def __str__(self):
        return self.name


class Domain(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return str(self.name)


class GeneList(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=400, blank=True, null=True)

    def __str__(self):
        return str(self.name)


class Gene(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name='genes')
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400, blank=True, null=True)
    domains = models.ManyToManyField(Domain)
    genelists = models.ManyToManyField(GeneList)
    correlations = models.ManyToManyField('self', through='GeneCorrelation', symmetrical=True)

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
    spearman_pvalue = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    pearson_r = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    pearson_pvalue = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)

    class Meta:
        unique_together = ("gene", "gene2")

    def __str__(self):
        return f"{self.gene.name} - {self.gene2.name}"


class MetacellGeneExpression(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='mge')
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE)
    metacell = models.ForeignKey(Metacell, on_delete=models.CASCADE)
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
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE)
    single_cell = models.ForeignKey(SingleCell, on_delete=models.CASCADE)
    umi_raw = models.FloatField(blank=True, null=True)
    umifrac = models.FloatField(blank=True, null=True)

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
        return self.gene.metacellgeneexpression_set.all()

    def __str__(self):
        return f"{self.orthogroup} {self.gene}"
