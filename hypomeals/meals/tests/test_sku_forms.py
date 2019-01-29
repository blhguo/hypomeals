from django.core.exceptions import ValidationError

from meals import utils
from meals.forms import CsvModelAttributeField, SkuFilterForm
from meals.models import Vendor, Ingredient, Upc, ProductLine, Sku, SkuIngredient
from .test_base import BaseTestCase


class SkuFormsBaseTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.last_ingredient = 0
        self.last_sku = 0
        self.last_product_line = 0

    def create_ingredient(self, name=None):
        self.last_ingredient += 1
        number = self.last_ingredient
        if name is None:
            name = f"Ingr #{number}"
        ingr = Ingredient.objects.filter(name=name)
        if ingr.exists():
            return ingr[0]
        vendor = Vendor.objects.create(info="Test vendor")
        self.logger.info("Creating Ingr %s", name)
        return Ingredient.objects.create(
            name=name,
            number=number,
            vendor=vendor,
            size="10kg",
            cost=10,
            comment=f"Test ingredient {number}",
        )

    def create_upc(self, upc_number=None):
        if isinstance(upc_number, Upc):
            return upc_number
        if upc_number is None:
            upc_number = utils.generate_random_upc()
        if not utils.is_valid_upc(upc_number):
            raise AssertionError(f"'{upc_number}' is not a valid UPC")
        return Upc.objects.get_or_create(upc_number=upc_number)[0]

    def create_product_line(self, name=None):
        self.last_product_line += 1
        if name is None:
            name = f"Test Product Line {self.last_product_line}"
        return ProductLine.objects.create(name=name)

    def create_sku(
        self, name=None, case_upc=None, unit_upc=None, product_line=None, ingredients=()
    ):
        self.last_sku += 1
        number = self.last_sku
        if name is None:
            name = f"SKU #{number}"
        case_upc = self.create_upc(case_upc)
        unit_upc = self.create_upc(unit_upc)
        if not isinstance(product_line, ProductLine):
            product_line = self.create_product_line()
        if ingredients:
            if not isinstance(ingredients[0], Ingredient):
                ingredients = [self.create_ingredient(name) for name in ingredients]
        instance = Sku.objects.create(
            name=name,
            number=number,
            case_upc=case_upc,
            unit_upc=unit_upc,
            count=1,
            product_line=product_line,
        )
        [
            SkuIngredient.objects.create(
                sku_number=instance, ingredient_number=ingredient, quantity=1
            )
            for ingredient in ingredients
        ]
        return instance


class TestCsvModelAttributeField(SkuFormsBaseTest):
    def test_ignore_empty(self):
        [self.create_ingredient(name) for name in ["apple", "pear"]]
        form = CsvModelAttributeField(Ingredient, attr="name")
        test_cases = ["", " ", ",", "apple,", "pear"]
        expected_values = [set(), set(), set(), {"apple"}, {"pear"}]
        for test_case, expected in zip(test_cases, expected_values):
            result = form.clean(test_case)
            self.assertEquals(expected, result, "Empty result should not be returned")

    def test_nonexistent_ingredients(self):
        """Nonexistent ingredients should cause an exception to be raised"""
        form = CsvModelAttributeField(Ingredient, attr="name")
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
        with self.assertRaises(ValidationError, expected_regex=r"kiwi fruit") as cm:
            form.clean("apple, pear, kiwi fruit")


class TestSkuFilterForm(SkuFormsBaseTest):
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
