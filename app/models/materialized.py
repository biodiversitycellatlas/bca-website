"""
Django models that create PostgreSQL materialized views for optimized querying
of statistics.
"""

from django.db import models, connection
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField

from colorfield.fields import ColorField
import re
import hashlib

from django.db.models import F, Count, Avg, Sum, OuterRef, Subquery

from .models import Metacell
from ..functions import RowNumber


class MaterializedModel(models.Model):
    """ Abstract class for models with materialized views. """
    materialized_id = models.AutoField(primary_key=True)

    class Meta:
        abstract = True
        managed = False

    @classmethod
    def perform_subquery(cls, obj, expr):
        """ Return subquery for aggregated statistics per object. """
        subquery = Subquery(obj.filter(id=OuterRef('id')).annotate(
            expr=expr
        ).values('expr')[:1])
        return subquery

    @classmethod
    def execute_sql(cls, sql):
        """ Executes raw SQL query. """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
        except Exception as e:
            print(f"Error executing SQL: {e}")

    @classmethod
    def create_materialized_view(cls, queryset):
        """ Creates a materialized view from a given queryset. """
        table = cls._meta.db_table
        queryset = queryset.annotate(materialized_id=RowNumber())
        select = str(queryset.query)
        sql = f'CREATE MATERIALIZED VIEW IF NOT EXISTS {table} AS {select};'
        cls.execute_sql(sql)

    @classmethod
    def refresh(cls):
        """ Refreshes the materialized view. """
        table = cls._meta.db_table
        sql = f'REFRESH MATERIALIZED VIEW {table};'
        cls.execute_sql(sql)


class MetacellCount(MaterializedModel):
    metacell = models.ForeignKey(Metacell, on_delete=models.CASCADE)
    cells = models.IntegerField()
    umis = models.IntegerField()

    @classmethod
    def create(cls):
        """ Creates the materialized view for metacell statistics. """

        # Get total number of cells and UMIs per metacell
        metacell = Metacell.objects
        cells = cls.perform_subquery(metacell, Count('singlecell'))
        umis = cls.perform_subquery(metacell, Sum('metacellgeneexpression__umi_raw'))

        queryset = metacell.annotate(
            metacell_id=F('id'),
            cells=cells,
            umis=umis
        ).values('metacell_id', 'cells', 'umis')
        cls.create_materialized_view(queryset)
