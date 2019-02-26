#pylint: disable-msg=protected-access,unused-argument,not-callable
import copy
import logging
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
from meals.models import Sku, Formula, ProductLine, Upc, \
    Vendor, Ingredient, FormulaIngredient, \
    ManufacturingLine, SkuManufacturingLine, Unit
import re

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
            for unique_keys in self.unique_fields:
                values = tuple(
                    converted_row[self.field_dict[unique_key]]
                    for unique_key in unique_keys
                )
                if values in self.unique_dict[unique_keys]:
                    key_name = tuple(
                        self.fields[field].verbose_name for field in unique_keys
                    )
                    raw_values = tuple(
                        row[self.field_dict[unique_key]] for unique_key in unique_keys
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
        "product_line": "Product Line Name",
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

        ml_short_set_string = row["ML Shortnames"]
        ml_short_set = ml_short_set_string.split(", ")
        ml_short = ManufacturingLine.objects.filter(shortname__in=ml_short_set)
        if len(ml_short) != len(ml_short_set):
            #we have an error, some manufacturing lines were attempted to be imported
            raise IntegrityException(
                message=f"Cannot import SKU #{row['SKU#']}",
                line_num=line_num,
                referring_name="SKU",
                referred_name="Manufacturing Line",
                fk_name="Manufacturing Line Name",
                fk_value=row["ML Shortnames"],
            )
        else:
            row["ML Shortnames"] = ml_short
        return row

    def _construct_instance(self, row, line_num=None):
        instance = self.model()
        for field_name in self.fields:
            setattr(instance, field_name, row[self.field_dict[field_name]])
        #setattr(instance, "manufacturing_lines", row["ML Shortnames"])
        for ML_obj in row["ML Shortnames"]:
            SML = SkuManufacturingLine(sku=instance,
                                       line=ML_obj,
                                       rate=row["Rate"])
            SML.save()
        return instance


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
        "unit": "Unit",
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
        if row["Size"]:
            strToParse = row["Size"]
            try:
                numbers = re.search('^(\d*\.?\d+)\s*(\D.*|)$', strToParse).group(1)
                units = re.search('^(\d*\.?\d+)\s*(\D.*|)$', strToParse).group(2)
                if not (numbers or units):
                    raise IntegrityException(
                        message=f"Cannot import Ingredient #{row['Ingr#']}",
                        line_num=line_num,
                        referring_name="Ingredient",
                        referred_name="Units",
                        fk_name="Unit",
                        fk_value=row["Size"],
                    )
                else:
                    row["Size"] = numbers
                    print(units)
                    row["Unit"] = Unit.objects.get(symbol=units)
                    print(row["Unit"])
            except AttributeError:
                raise IntegrityException(
                    message=f"Cannot import Ingredient #{row['Ingr#']}",
                    line_num=line_num,
                    referring_name="Ingredient",
                    referred_name="Units",
                    fk_name="Unit",
                    fk_value=row["Size"],
                )
        return row


class FormulaImporter(Importer):

    file_type = "formulas"
    header = ["Formula#", "Name", "Ingr#", "Quantity", "Comment"]
    field_dict = {
        "name": "Name",
        "number": "Formula#",
        "ingredients": "Ingr#",
        "comment": "Comment",
    }
    model = Formula
    model_name = "Formula"

    def _construct_instance(self, row, line_num=None):
        instance = self.model()
        for field_name in self.fields:
            if field_name is not "number":
                setattr(instance, field_name, row[self.field_dict[field_name]])
            elif not Formula.objects.get(number=row['Formula#']):
                setattr(instance, field_name, row[self.field_dict[field_name]])

        FI = row["ingredient"]
        newFormulaIngredient = FormulaIngredient.objects.create(formula=self, ingredient=Ingredient.objects.get(number=FI), quantity=row["Quantity"])
        newFormulaIngredient.save()
        return instance

    def _process_row(self, row, line_num=None):
        db_formula = Formula.objects.filter(number=row["Formula#"])
        if db_formula.exists():
            FormulaIngredient.objects.filter(formula=db_formula).delete()
            #add code to blow away current DB entry, I think this removes the dependent FormulaIngredients, but not the Ingredients themselves.
            #I'm not sure how that interacts with SKUs, should be fine
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
