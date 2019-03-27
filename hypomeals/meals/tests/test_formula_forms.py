# pylint: disable-msg=expression-not-assigned
import logging
from decimal import Decimal
from unittest import skip

from django.http import HttpResponseRedirect
from django.urls import reverse

from meals.forms import FormulaFormset
from meals.models import Ingredient, User
from .test_base import BaseTestCase

logger = logging.getLogger(__name__)


@skip("Skip it for now")
class FormulaFormsTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.initial_data = {"form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000"}

    def _get_form_data(self, ingredients, quantities):
        self.assertEqual(
            len(ingredients), len(quantities), "Expected two lists of same length"
        )
        self.initial_data["form-TOTAL_FORMS"] = str(len(ingredients))
        self.initial_data["form-INITIAL_FORMS"] = "0"

        for i, (ingr, quan) in enumerate(zip(ingredients, quantities)):
            prefix = f"form-{i}-"
            self.initial_data[f"{prefix}ingredient"] = (
                ingr.name if isinstance(ingr, Ingredient) else ingr
            )

            self.initial_data[f"{prefix}quantity"] = quan
        return self.initial_data

    def test_nonexistent_ingredients(self):
        """Tests that formset returns error when ingredient doesn't exist"""
        [
            self.create_ingredient(name)
            for name in ["apple", "chocolate", "cheese", "banana", "pear"]
        ]
        sku = self.create_sku()
        form_data = self._get_form_data(["apple", "chocolate", "strawberry"], [1, 2, 3])
        formset = FormulaFormset(form_data, form_kwargs={"sku": sku})
        self.assertFalse(formset.is_valid(), "Formset should not be valid")
        self.assertFalse(formset.errors[0], "First form has no error")
        self.assertFalse(formset.errors[1], "Second form has no error")
        errors = formset.errors[2]["ingredient"]
        self.assertEqual(1, len(errors), "Only one ingredient doesn't exist.")
        self.assertRegex(str(errors), r"strawberry", msg="Strawberry shouldn't exist.")

    def test_create_formula(self):
        """Tests that formula overrides original"""
        formula = self.create_formula(
            name="chocolate cake", ingredients=["chocolate", "cheese", "cream"]
        )
        sku = self.create_sku(name="chocolate cake", formula=formula)
        self.create_ingredient("cocoa")
        form_data = self._get_form_data(
            ["chocolate", "cheese", "cocoa"], [Decimal(1.0), Decimal(2.0), Decimal(3.0)]
        )
        self.client.force_login(
            User.objects.create_superuser(
                username="test_user", email="abc@example.com", password="123456"
            )
        )
        resp = self.client.post(
            reverse("edit_formula", args=(sku.formula.number,)), data=form_data
        )
        self.assertEqual(
            resp.status_code,
            HttpResponseRedirect.status_code,
            "Redirect should happen after processing form",
        )

        formula = sku.formula.formulaingredient_set.values(
            "ingredient__name", "quantity"
        )
        ingr_dict = {ingr["ingredient__name"]: ingr["quantity"] for ingr in formula}
        self.assertDictEqual(
            {"chocolate": Decimal(1.0), "cheese": Decimal(2.0), "cocoa": Decimal(3.0)},
            ingr_dict,
            "Formula should be exactly what was supplied.",
        )
