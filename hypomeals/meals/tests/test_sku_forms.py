# pylint: disable-msg=expression-not-assigned
from unittest import skip

from django.core.exceptions import ValidationError
from django.forms import forms
from django.template import Engine, Template, Context
from django.urls import reverse

from meals.forms import CsvAutocompletedField, SkuFilterForm
from meals.models import Ingredient
from .test_base import BaseTestCase


class TestCsvAutocompletedField(BaseTestCase):
    def test_ignore_empty(self):
        [self.create_ingredient(name) for name in ["apple", "pear"]]
        field = CsvAutocompletedField(Ingredient, attr="name", data_source=None)
        test_cases = ["", " ", ",", "apple,", "pear"]
        expected_values = [set(), set(), set(), {"apple"}, {"pear"}]
        for test_case, expected in zip(test_cases, expected_values):
            result = field.clean(test_case)
            self.assertEqual(expected, result, "Empty result should not be returned")

    def test_nonexistent_ingredients(self):
        """Nonexistent ingredients should cause an exception to be raised"""
        field = CsvAutocompletedField(Ingredient, attr="name", data_source=None)
        [
            self.create_ingredient(name)
            for name in [
                "apple",
                "pear",
                "berry",
                "banana",
                "dragonfruit",
                "watermelon",
            ]
        ]
        with self.assertRaises(ValidationError, expected_regex=r"kiwi fruit"):
            field.clean("apple, pear, kiwi fruit")

    def _render_field(self, field):
        form = type("TestForm", (forms.Form,), {"test_field": field})()
        template_engine = Engine.get_default()
        return Template("{{ form.test_field }}", engine=template_engine).render(
            context=Context({"form": form})
        )

    def test_autocomplete_attrs(self):
        """Tests that autocomplete attrs are correctly rendered on HTML elements"""
        field = CsvAutocompletedField(
            Ingredient, attr="name", data_source=reverse("autocomplete_ingredients")
        )
        rendered = self._render_field(field)
        self.assertIn(
            f"data-autocomplete-url=\"{reverse('autocomplete_ingredients')}\"",
            rendered,
            "'data-autocomplete-url' should be in rendered HTML",
        )
        self.assertIn("meals-autocomplete meals-autocomplete-multiple", rendered)


@skip("Pending model update migration")
class TestSkuFilterForm(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.form_data = {
            "page_num": 1,
            "num_per_page": -1,
            "sort_by": "name",
            "keyword": "",
            "ingredients": "",
            "product_lines": "",
        }

    def test_query_keyword(self):
        names = ["tomato soup", "cheesecake", "peanut butter", "jelly", "whipped cream"]
        [self.create_sku(name=name) for name in names]
        self.form_data["keyword"] = "tomato"
        form = SkuFilterForm(data=self.form_data)
        if not form.is_valid():
            self.logger.info(form.errors)
        self.assertTrue(form.is_valid(), "Form should be valid")
        results = form.query().object_list
        self.assertEqual(1, len(results), "There should only be one match")
        self.assertEqual(
            "tomato soup", results[0].name, "The match should be 'tomato soup'"
        )

    def test_query_ingredients(self):
        tomato_soup = self.create_sku(
            name="tomato soup", ingredients=("tomato", "water")
        )
        cigarette = self.create_sku(
            name="cigarette", ingredients=("tobacco", "grass", "water")
        )
        test_cases = ["grass,", "water"]
        expected_matches = [{cigarette}, {tomato_soup, cigarette}]
        for test_case, expected in zip(test_cases, expected_matches):
            self.form_data["ingredients"] = test_case
            form = SkuFilterForm(data=self.form_data)
            self.assertTrue(form.is_valid(), "Form should be valid")
            results = form.query().object_list
            self.assertSetEqual(expected, set(results), f"Expected={expected}")
