#pylint: disable-msg=protected-access,unused-argument,not-callable
import copy
import logging
import re
from abc import ABC
from collections import defaultdict
from typing import List, Dict, Any, Tuple

from django.db.models import Model, AutoField, Field

from meals import utils
from meals.exceptions import (
    IntegrityException,
    AmbiguousRecordException,
    CollisionException,
    DuplicateException,
)
from meals.models import Sku, ProductLine, Upc, Vendor, Ingredient, FormulaIngredient, \
    ManufacturingLine, Formula

logger = logging.getLogger(__name__)


class Importer(ABC):

    file_type: str = ""
    primary_key: Field = None
    header: List[str] = []
    model: Model = None
    model_name: str = ""
    fields = {}
    field_dict: Dict[str, str] = {}
    unique_fields = []

    def __init__(self):
        model = self.model
        self.instances: List[model] = []
        self.collisions: List[CollisionException] = []
        self.unique_dict: Dict[Tuple[str, ...], Any] = defaultdict(dict)
        if self.model is not None:
            self.fields = {
                field.name: field
                for field in self.model._meta.fields
                if not isinstance(field, AutoField)
            }
            self.unique_fields = [
                (field_name,)
                for field_name, field in self.fields.items()
                if field.unique
            ] + list(self.model._meta.unique_together)

    def do_import(self, reader, filename=None):
        num_processed = 0
        for line_num, row in enumerate(reader, start=2):
            converted_row = self._process_row(copy.copy(row), line_num)
            instance = self._construct_instance(converted_row)
            self._check_duplicates(row, converted_row, filename, line_num)
            try:
                instance = self._save(instance, filename, line_num)
            except CollisionException as e:
                self.collisions.append(e)
            else:
                self.instances.append(instance)

            num_processed += 1

        logger.info(
            "Processed %d records of model %s (%d collisions)",
            num_processed,
            self.model_name,
            len(self.collisions),
        )
        if not self.collisions:
            self._post_process()
        return self.instances, self.collisions

    def _check_duplicates(self, raw, converted, filename, line_num):
        for unique_keys in self.unique_fields:
            values = tuple(
                converted[self.field_dict[unique_key]]
                for unique_key in unique_keys
            )
            if values in self.unique_dict[unique_keys]:
                key_name = tuple(
                    self.fields[field].verbose_name for field in unique_keys
                )
                raw_values = tuple(
                    raw[self.field_dict[unique_key]] for unique_key in unique_keys
                )
                previous_line_num = self.unique_dict[unique_keys][values]
                raise DuplicateException(
                    f"{filename}:{line_num}: "
                    f"Cannot import {self.file_type} with {key_name} = "
                    f"'{raw_values}'.",
                    model_name=self.model_name,
                    key=key_name,
                    value=raw_values,
                    line_num=previous_line_num,
                )

            self.unique_dict[unique_keys][values] = line_num

    def _process_row(self, row, line_num=None):
        return row

    def _construct_instance(self, row, line_num=None):
        instance = self.model()
        for field_name in self.fields:
            setattr(instance, field_name, row[self.field_dict[field_name]])
        return instance

    def _save(self, instance, filename, line_num):
        """
        Tries to save a model. If duplicate occurs, check and see if two instances are
        identical: if so, the old instance is returned. Otherwise, raise a
        CollisionException to be handled later.
        :param instance: an instance of the model to be saved
        :return: the saved instance. If an identical record already exists, the previous
            record.
        """
        primary_key_value = getattr(instance, self.primary_key.name)
        model = instance.__class__
        matches = {}
        for field_name, field in self.fields.items():
            if field.primary_key:
                continue
            if not field.unique:
                continue
            if isinstance(field, AutoField):
                continue
            record = model.objects.filter(**{field_name: getattr(instance, field_name)})
            if record.exists() and record[0] not in matches.values():
                matches[field.verbose_name] = record[0]
            if len(matches) > 1:
                break
        if len(matches) > 1:
            raise AmbiguousRecordException(
                f"{filename}:{line_num}: Ambiguous record detected.", instance, matches
            )
        if primary_key_value:
            primary_match = model.objects.filter(
                **{self.primary_key.name: primary_key_value}
            )
            actual_match = primary_match[0] if primary_match.exists() else None
        else:
            actual_match = None
        if len(matches) == 1:
            if not actual_match:
                raise AmbiguousRecordException(
                    f"{filename}:{line_num}: Primary key did not match record while "
                    "other keys did.",
                    instance,
                    matches,
                )
            if next(iter(matches.values())) != actual_match:
                matches[self.primary_key.verbose_name] = actual_match
                raise AmbiguousRecordException(
                    f"{filename}:{line_num}: Ambiguous record detected.",
                    instance,
                    matches,
                )
        if actual_match:
            if model.compare_instances(actual_match, instance):
                # Identical instances should be ignored
                return instance
            raise CollisionException(actual_match, instance)
        instance.save()
        return instance

    def _post_process(self):
        pass


class SkuImporter(Importer):

    file_type = "skus"
    header = [
        "SKU#",
        "Name",
        "Case UPC",
        "Unit UPC",
        "Unit size",
        "Count per case",
        "Product Line Name",
        "Formula#",
        "Formula factor",
        "ML Shortnames",
        "Rate",
        "Comment",
    ]
    primary_key = Sku._meta.get_field("number")
    model = Sku
    model_name = "SKU"
    instances = []
    field_dict = {
        "number": "SKU#",
        "name": "Name",
        "case_upc": "Case UPC",
        "unit_upc": "Unit UPC",
        "unit_size": "Unit size",
        "count": "Count per case",
        "product_line": "PL Name",
        "formula": "Formula#",
        "formula_scale": "Formula factor",
        "manufacturing_lines": "ML Shortnames",
        "comment": "Comment",
    }

    def _process_row(self, row, line_num=None):
        raw_formula = row["Formula#"]

        formula_qs = Formula.objects.filter(number=raw_formula)
        if formula_qs.exists():
            row["Formula#"] = formula_qs[0]
        else:
            raise IntegrityException(
                message=f"Cannot import SKU #{row['SKU#']}",
                line_num=line_num,
                referring_name="SKU",
                referred_name="Product Line",
                fk_name="Formula",
                fk_value=row["Formula#"],
            )
        raw_case_upc = row["Case UPC"]
        print(utils.is_valid_upc(raw_case_upc))
        if utils.is_valid_upc(raw_case_upc):
            print("made it")
            row["Case UPC"] = Upc.objects.get_or_create(upc_number=raw_case_upc)[0]
            print(row['Case UPC'])
        raw_unit_upc = row["Unit UPC"]
        if utils.is_valid_upc(raw_unit_upc):
            row["Unit UPC"] = Upc.objects.get_or_create(upc_number=raw_unit_upc)[0]
        if row["Comment"] is None:
            row["Comment"] = ""
        product_line = ProductLine.objects.filter(name=row["Product Line Name"])
        if product_line.exists():
            row["Product Line Name"] = product_line[0]
        else:
            raise IntegrityException(
                message=f"Cannot import SKU #{row['SKU#']}",
                line_num=line_num,
                referring_name="SKU",
                referred_name="Product Line",
                fk_name="Product Line Name",
                fk_value=row["Product Line Name"],
            )

        # Duplicated shortnames are ignored
        raw_ml = set(re.split(r",\s*", row["ML Shortnames"]))
        ml_objs = ManufacturingLine.objects.filter(shortname__in=raw_ml)
        found = set(ml_objs.values_list("shortname", flat=True))
        missing = raw_ml - found
        if missing:
            raise IntegrityException(
                message=f"Cannot import SKU #{row['SKU#']}: "
                "manufacturing line(s) do not exist.",
                line_num=line_num,
                referring_name="SKU",
                referred_name="Manufacturing Line",
                fk_name="ML Shortnames",
                fk_value=", ".join(missing),
            )

        row["ML Shortnames"] = ml_objs
        return row


class IngredientImporter(Importer):

    file_type = "ingredients"
    header = ["Ingr#", "Name", "Vendor Info", "Size", "Cost", "Comment"]
    primary_key = Ingredient._meta.get_field("number")
    model = Ingredient
    model_name = ("Ingredient",)
    field_dict = {
        "number": "Ingr#",
        "name": "Name",
        "vendor": "Vendor Info",
        "size": "Size",
        "cost": "Cost",
        "comment": "Comment",
    }

    def _process_row(self, row, line_num=None):
        vendor = Vendor.objects.filter(info=row["Vendor Info"])
        if vendor.exists():
            row["Vendor Info"] = vendor[0]
        else:
            row["Vendor Info"] = Vendor.objects.create(info=row["Vendor Info"])
        if row["Comment"] is None:
            row["Comment"] = ""
        return row


class FormulaImporter(Importer):

    file_type = "formulas"
    header = ["SKU#", "Ingr#", "Quantity"]
    field_dict = {
        "sku_number": "SKU#",
        "ingredient_number": "Ingr#",
        "quantity": "Quantity",
    }
    model = FormulaIngredient
    model_name = "Formula"

    def _process_row(self, row, line_num=None):
        sku = Sku.objects.filter(number=row["SKU#"])
        if not sku.exists():
            raise IntegrityException(
                message="Cannot import Formula",
                line_num=line_num,
                referring_name="Formula",
                referred_name="SKU",
                fk_name="SKU#",
                fk_value=row["SKU#"],
            )
        row["SKU#"] = sku[0]
        ingr = Ingredient.objects.filter(number=row["Ingr#"])
        if not ingr.exists():
            raise IntegrityException(
                message="Cannot import Formula",
                line_num=line_num,
                referring_name="Formula",
                referred_name="Ingredient",
                fk_name="Ingr#",
                fk_value=row["Ingr#"],
            )
        row["Ingr#"] = ingr[0]
        return row

    def _save(self, instance, filename, line_num):
        # Formulas need to be saved together. Logic in _post_process()
        return instance

    def _post_process(self):
        sku_numbers = {formula.sku_number.number for formula in self.instances}
        FormulaIngredient.objects.filter(sku_number__in=sku_numbers).delete()
        for instance in self.instances:
            instance.save()


class ProductLineImporter(Importer):

    file_type = "product_lines"
    header = ["Name"]
    field_dict = {"name": "Name"}
    model = ProductLine
    model_name = "Product Line"
    primary_key = ProductLine._meta.get_field("name")

    def _save(self, instance, filename, line_num):
        existing = self.model.objects.filter(name=instance.name)
        if existing.exists():
            return existing[0]
        instance.save()
        return instance


IMPORTERS = {
    "skus": SkuImporter,
    "ingredients": IngredientImporter,
    "product_lines": ProductLineImporter,
    "formulas": FormulaImporter,
}
