# pylint: disable-msg=expression-not-assigned

import logging
import sys

from django.test import TestCase

from meals import utils
from meals.models import Ingredient, Vendor, Upc, ProductLine, SkuIngredient, Sku


class BaseTestCase(TestCase):
    def setUp(self):
        self.logger = logging.getLogger(__name__)
        self._log_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self._log_handler)

        self.last_ingredient = 0
        self.last_sku = 0
        self.last_product_line = 0
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

    def tearDown(self):
        self.logger.removeHandler(self._log_handler)
        super().tearDown()
