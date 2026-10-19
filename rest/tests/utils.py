from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase

from app import models
from rest.filters import SpeciesFilter
from rest.utils import filters as filter_utils
from rest.utils.utils import get_path_param


class FilterChoiceErrorTests(TestCase):
    def setUp(self):
        filter_utils._cached_species_choices = None
        filter_utils._cached_dataset_choices = None

    def tearDown(self):
        filter_utils._cached_species_choices = None
        filter_utils._cached_dataset_choices = None

    @patch("rest.utils.filters.check_model_exists", return_value=True)
    @patch("rest.utils.filters.models.Species.objects.all", side_effect=DatabaseError)
    def test_species_choices_handle_database_error(self, _all, _exists):
        self.assertEqual(filter_utils.update_species_choices(), [])

    @patch("rest.utils.filters.check_model_exists", return_value=True)
    @patch("rest.utils.filters.models.Dataset.objects.all", side_effect=DatabaseError)
    def test_dataset_choices_handle_database_error(self, _all, _exists):
        self.assertEqual(filter_utils.update_dataset_choices(), [])

    @patch("rest.utils.filters.connection.introspection.table_names", side_effect=DatabaseError)
    def test_model_check_handles_database_error(self, _table_names):
        self.assertFalse(filter_utils.check_model_exists(models.Species))


class PathParameterTests(TestCase):
    def test_path_parameter_falls_back_when_filter_initialization_fails(self):
        class BrokenFilter:
            def __init__(self):
                raise RuntimeError("Unavailable choices")

        with self.assertLogs("rest.utils.utils", level="WARNING"):
            parameter = get_path_param("species", BrokenFilter)

        self.assertEqual(parameter.name, "species")

    def test_empty_species_query_returns_queryset_unchanged(self):
        queryset = models.Species.objects.all()
        self.assertIs(SpeciesFilter(queryset=queryset).query(queryset, "q", ""), queryset)
