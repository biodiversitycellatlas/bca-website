from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField

from colorfield.fields import ColorField
import re


class Species(models.Model):
    common_name     = models.CharField(max_length=100, unique=True)
    scientific_name = models.CharField(max_length=100, unique=True)
    description     = models.TextField(blank=True, null=True)
    image_url       = models.URLField(blank=True, null=True)
    id              = models.BigIntegerField(default=2222, unique=True, primary_key=True)

    @property
    def species_underscore(self):
        """
        Returns scientific name with underscores to use in URL.

        Example:
            For 'Trichoplax adhaerens', returns 'Trichoplax_adhaerens'.
        """
        return self.scientific_name.replace(" ", "_")

    @property
    def image_source(self):
        """
        Get image source based on URL domain.

        Example:
            For 'https://test.wikimedia.org/path/img.jpg', returns 'Wikimedia'.
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


class Metacell(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    x = models.FloatField()
    y = models.FloatField()
    type = models.CharField(max_length=100, blank=True, null=True)
    color = ColorField(default='#AAAAAA')

    class Meta:
        unique_together = ["name", "species"]

    def __str__(self):
        return self.name


class SingleCell(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    metacell = models.ForeignKey(Metacell, on_delete=models.CASCADE, blank=True, null=True)
    x = models.FloatField()
    y = models.FloatField()

    class Meta:
        unique_together = ["name", "species"]

    def __str__(self):
        return f"{self.id}"


class MetacellLink(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    metacell = models.ForeignKey(Metacell, on_delete=models.CASCADE, related_name='metacell')
    metacell2 = models.ForeignKey(Metacell, on_delete=models.CASCADE, related_name='metacell2')

    class Meta:
        unique_together = ["species", "metacell", "metacell2"]

    def clean(self):
        if self.metacell == self.metacell2:
            raise ValidationError("Metacells cannot be linked to themselves.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Gene(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400, blank=True, null=True)
    domains = ArrayField(models.CharField(max_length=30), blank=True, null=True)

    class Meta:
        unique_together = ["name", "species"]

    def __str__(self):
        return str(self.name)

class MetacellGeneExpression(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE)
    metacell = models.ForeignKey(Metacell, on_delete=models.CASCADE)
    value = models.FloatField()

    class Meta:
        unique_together = ["gene", "metacell", "species"]
        verbose_name = "metacell gene expression"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.gene} {self.metacell}"
