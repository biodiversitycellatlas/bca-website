from django.test import SimpleTestCase

from app.templatetags.string_extras import (
    split,
    startswith,
    human_number,
    intspace,
)


class StringExtrasTests(SimpleTestCase):
    def test_split_default_delimiter(self):
        assert split("a,b,c") == ["a", "b", "c"]

    def test_split_custom_delimiter(self):
        assert split("a|b|c", "|") == ["a", "b", "c"]

    def test_startswith_true(self):
        assert startswith("django", "dja")

    def test_startswith_false(self):
        assert not startswith("django", "jan")

    def test_human_number_under_1000(self):
        assert human_number(950) == "950"

    def test_human_number_thousands(self):
        assert human_number(1500) == "2K"

    def test_human_number_millions(self):
        assert human_number(2_000_000) == "2M"

    def test_human_number_invalid(self):
        assert human_number("abc") == "abc"

    def test_intspace_integer(self):
        assert intspace(1000000) == "1 000 000"

    def test_intspace_float_integer(self):
        assert intspace(1000.0) == "1 000"

    def test_intspace_float(self):
        assert intspace(1234.56) == "1 234.56"

    def test_intspace_invalid(self):
        assert intspace("abc") == "abc"
