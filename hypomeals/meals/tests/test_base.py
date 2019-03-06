# pylint: disable-msg=expression-not-assigned

import logging
import sys

from django.test import TestCase

from meals import utils
from meals.models import (
    Ingredient,
    Vendor,
    Upc,
    ProductLine,
    FormulaIngredient,
    Sku,
    Unit,
    Formula,
    ManufacturingLine,
    SkuManufacturingLine,
)


class BaseTestCase(TestCase):
    def setUp(self):
        self.logger = logging.getLogger(__name__)
        self._log_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self._log_handler)

        self.last_ingredient = 0
        self.last_sku = 0
        self.last_product_line = 0
        self.last_formula = 0
        self.last_mfg_line = 0
        self.kg = Unit.objects.get(symbol="kg")
        super().setUp()

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
            size=10,
            unit=self.kg,
            cost=10,
            comment=f"Test ingredient {number}",
        )

    def create_upc(self, upc_number=None):
        if isinstance(upc_number, Upc):
            return upc_number
        if upc_number is None:
            upc_number = utils.generate_random_upc()
        if not utils.is_valid_upc(upc_number) or str(upc_number)[0] in ['2', '3', '4', '5']:
            raise AssertionError(f"'{upc_number}' is not a valid UPC")
        return Upc.objects.get_or_create(upc_number=upc_number)[0]

    def create_formula(self, name=None, ingredients=()):
        self.last_formula += 1
        number = self.last_formula
        if name is None:
            name = f"Formula #{number}"
        formula = Formula.objects.create(
            name=name, number=number, comment=f"Test formula {number}"
        )
        if ingredients:
            if not isinstance(ingredients[0], Ingredient):
                ingredients = [self.create_ingredient(name) for name in ingredients]
        [
            FormulaIngredient.objects.create(
                formula=formula, ingredient=ingredient, quantity=1
            )
            for ingredient in ingredients
        ]
        return formula

    def create_product_line(self, name=None):
        self.last_product_line += 1
        if name is None:
            name = f"Test Product Line {self.last_product_line}"
        return ProductLine.objects.create(name=name)

    def create_sku(
        self,
        name=None,
        case_upc=None,
        unit_upc=None,
        product_line=None,
        formula=None,
        formula_scale=None,
        ingredients=(),
        manufacturing_lines=(),
    ):
        self.last_sku += 1
        number = self.last_sku
        if name is None:
            name = f"SKU #{number}"
        case_upc = self.create_upc(case_upc)
        unit_upc = self.create_upc(unit_upc)
        if not isinstance(product_line, ProductLine):
            product_line = self.create_product_line(name=product_line)

        if formula:
            if not isinstance(formula, Formula):
                raise RuntimeError(
                    "Formula must be a formula instance; or specify "
                    "a list of ingredients instead."
                )
        else:
            if ingredients:
                formula = self.create_formula(ingredients=ingredients)
            else:
                formula = self.create_formula(ingredients=self.create_ingredient())

        instance = Sku.objects.create(
            name=name,
            number=number,
            case_upc=case_upc,
            unit_upc=unit_upc,
            count=1,
            product_line=product_line,
            formula=formula,
            formula_scale=formula_scale or 1.0,
            comment=f"Test SKU #{number}",
        )

        if manufacturing_lines:
            if not isinstance(manufacturing_lines[0], ManufacturingLine):
                manufacturing_lines = [
                    self.create_manufacturing_line(line) for line in manufacturing_lines
                ]
            [
                SkuManufacturingLine.objects.create(
                    sku=instance, manufacturing_line=line, rate=1.0
                )
                for line in manufacturing_lines
            ]

        return instance

    def create_manufacturing_line(self, name=None):
        self.last_mfg_line += 1
        number = self.last_mfg_line
        name = name or f"ML{number}"
        return ManufacturingLine.objects.create(
            name=f"ML{number}",
            shortname=name[-5:],
            comment=f"Test ManufacturingLine #{number}",
        )

    def ajax_get(self, *args, **kwargs):
        kwargs.update({"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        return self.client.get(*args, **kwargs)

    def ajax_post(self, *args, **kwargs):
        kwargs.update({"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        return self.client.post(*args, **kwargs)

    def assertInAny(self, member, containers, msg=""):
        """
        Asserts that member is found in any of the containers. Useful when searching
        through some log output. E.g.,

        >>> with self.assertLogs(logger, level="INFO") as cm:
        ...     do_stuff()
        >>> self.assertInAny("My super cool message", cm.output)
        :param msg: a message to print when assertion fails
        :param member: a member to search for
        :param containers: an iterable of containers to search through
        :return: None
        :raises: AssertionError if member is not found in any of the containers
        """
        for container in containers:
            if member in container:
                return
        raise AssertionError(f"'{member}' not found in {containers}: {msg}")

    def tearDown(self):
        self.logger.removeHandler(self._log_handler)
        super().tearDown()
