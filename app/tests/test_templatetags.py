from django.test import SimpleTestCase

from app.templatetags.string_extras import (
    split,
    startswith,
    human_number,
    intspace,
)


class StringExtrasTests(SimpleTestCase):
    def test_split_default_delimiter(self):
        self.assertEqual(split("a,b,c"), ["a", "b", "c"])

    def test_split_custom_delimiter(self):
        self.assertEqual(split("a|b|c", "|"), ["a", "b", "c"])

    def test_startswith_true(self):
        self.assertTrue(startswith("django", "dja"))

    def test_startswith_false(self):
        self.assertFalse(startswith("django", "jan"))

    def test_human_number_under_1000(self):
        self.assertEqual(human_number(950), "950")

    def test_human_number_thousands(self):
        self.assertEqual(human_number(1500), "2K")

    def test_human_number_millions(self):
        self.assertEqual(human_number(2_000_000), "2M")

    def test_human_number_invalid(self):
        self.assertEqual(human_number("abc"), "abc")

    def test_intspace_integer(self):
        self.assertEqual(intspace(1000000), "1 000 000")

    def test_intspace_float_integer(self):
        self.assertEqual(intspace(1000.0), "1 000")

    def test_intspace_float(self):
        self.assertEqual(intspace(1234.56), "1 234.56")

    def test_intspace_invalid(self):
        self.assertEqual(intspace("abc"), "abc")
