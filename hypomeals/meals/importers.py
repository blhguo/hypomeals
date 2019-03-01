# pylint: disable-msg=protected-access,unused-argument,not-callable
import copy
import csv
import itertools
import logging
import re
from abc import ABC
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Tuple, Optional, Type

from django.db import transaction
from django.db.models import Model, AutoField, Field
from django.db.models.fields.related import RelatedField

from meals import utils
from meals.exceptions import (
    IntegrityException,
    AmbiguousRecord,
    CollisionException,
    DuplicateException,
    UserFacingException,
    Skip,
    IdenticalRecord,
    CollisionOccurredException,
)
from meals.models import (
    Sku,
    ProductLine,
    Upc,
    Vendor,
    Ingredient,
    FormulaIngredient,
    ManufacturingLine,
    Formula,
    Unit,
    SkuManufacturingLine,
)

logger = logging.getLogger(__name__)


class Importer(ABC):

    file_type: str = ""
    primary_key: Field = None
    header: List[str] = []
    model: Model = None
    model_name: str = ""  # name of the model. Ideally human-readable.
    fields = {}  # mapping of all fields in the model
    m2m = {}  #  a mapping of all ManyToManyFields of the model
    field_dict: Dict[str, str] = {}
    unique_fields = []

    def __init__(self, filename: str = None):
        model = self.model
        self._instances: List[model] = []
        self._collisions: List[CollisionException] = []
        self._ignored: List[model] = []
        self.unique_dict: Dict[Tuple[str, ...], Any] = defaultdict(dict)
        self.filename = filename or "<unknown file>"
        self._is_bound = False
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

    @property
    def is_bound(self):
        """Whether do_import has been called at least once"""
        return self._is_bound

    @property
    def instances(self):
        return self._instances

    @property
    def collisions(self):
        return self._collisions

    @property
    def ignored(self):
        return self._ignored

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.filename} is_bound:{self.is_bound}>"

    @transaction.atomic
    def do_import(self, lines: List[str]) -> Tuple[int, int, int]:
        """
        This is the core of every importer, and performs the bulk of all functionality.

        It does a few things, all of which are delegated to private methods so they can
        be overriden for different object models, in this order:
        * Apply _process_row to the raw row data
        * Call _construct_instance to create a new instance of the record
        * Call _check_duplicates on the new instance to check for duplicates in the same
            file
        * Call _save to detect duplicates / ambiguous records / collisions in the
            database
        * Call _save_m2m to save any ManyToManyRelationship, for example, the
            ingredients to a formula.
        * Call _post_process to handle any data that requires special handling, for
            example, saving FormulaIngredients.

        In these circumstances, import fails with all operations rolled back:
        * When any of the processing returns any exception
        * When a duplicate is detected within the file
        * When an ambiguous record is detected with existing database records
        * When at least one collision is detected
        :param lines: a list of lines from the CSV file, usually as a result of a call
            to splitlines().
        :return: a 3-tuple of (inserted, updated, ignored) numbers of instances
        """
        reader = csv.DictReader(lines[1:], fieldnames=self.header, dialect="unix")
        num_processed = 0
        for line_num, row in enumerate(reader, start=2):
            try:
                converted_row = self._process_row(
                    copy.copy(row), self.filename, line_num
                )
                instance = self._construct_instance(converted_row)
                self._check_duplicates(row, converted_row, self.filename, line_num)
                instance = self._save(instance, self.filename, line_num)
                self._save_m2m(
                    instance, converted_row, self.filename, line_num
                )
            except UserFacingException as e:
                e.message = f"{self.filename}:{line_num}: " + e.message
                raise e
            except Skip:
                continue
            except CollisionException as e:
                self._collisions.append(e)
            except IdenticalRecord as e:
                self._ignored.append(e.record)
            else:
                self._instances.append(instance)

            num_processed += 1

        self._is_bound = True
        logger.info(
            "Processed %d records of model %s (%d collisions)",
            num_processed,
            self.model_name,
            len(self._collisions),
        )
        if not self._collisions:
            self._post_process()
        else:
            raise CollisionOccurredException
        return len(self.instances), len(self.collisions), len(self.ignored)

    @transaction.atomic
    def commit(self) -> Tuple[int, int, int]:
        """
        Force commits all instances, including collisions.
        :return: a 3-tuple (inserted, updated, ignored) of integers representing the
            numbers of instances in each category.
        """
        if not self.is_bound:
            raise UserFacingException(
                "Data corruption detected. Please try importing "
                "again. Error code: ENOTBOUND"
            )
        for instance in self.instances:
            self.__save(instance)

        for collision in self.collisions:
            collision.old_record.delete()
            self.__save(collision.new_record)

        self._post_process()
        return len(self.instances), len(self.collisions), len(self.ignored)

    def _check_duplicates(
        self,
        raw: Dict[str, str],
        converted: Dict[str, Any],
        filename: str,
        line_num: int,
    ) -> None:
        for unique_keys in self.unique_fields:
            values = tuple(
                converted[self.field_dict[unique_key]] for unique_key in unique_keys
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
                    f"Cannot import {self.model_name}.",
                    model_name=self.model_name,
                    key=key_name,
                    value=raw_values,
                    line_num=previous_line_num,
                )

            self.unique_dict[unique_keys][values] = line_num

    def _process_row(
        self, row: Dict[str, Any], filename: str = None, line_num: int = None
    ) -> Dict[str, Any]:
        return row

    def _construct_instance(
        self, row: Dict[str, Any], line_num: int = None
    ) -> Type[model]:
        instance = self.model()
        for field_name in self.fields:
            setattr(instance, field_name, row[self.field_dict[field_name]])

        return instance

    def __save(self, instance: Type[model]) -> None:
        """
        Saves an instance with ForeignKey objects that are potentially not committed to
        DB.
        :param instance: an instance to save
        """
        for field in self.model._meta.fields:
            if isinstance(field, RelatedField):
                fk = getattr(instance, field.name)
                fk.save()
                setattr(instance, field.name, fk)
                logger.info("Saved fk %s (#%d) %s", field.name, fk.pk, str(fk))
        instance.save()

    def _save_m2m(
        self,
        instance: Type[model],
        row: Dict[str, Any],
        filename: str = None,
        line_num: int = None,
    ) -> None:
        for field in self.model._meta.many_to_many:
            values = row[self.field_dict[field.name]]
            getattr(instance, field.attname).set(values)

    def _save(self, instance, filename, line_num) -> Type[model]:
        """
        Tries to save a model. If duplicate occurs, check and see if two instances are
        identical: if so, a IdenticalRecord is raised. Otherwise, a
        CollisionException is raised to be handled later. If the record is ambiguous,
        raise a AmbiguousRecord.
        :param instance: an instance of the model to be saved
        :return: the saved instance.
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
            raise AmbiguousRecord(f"Ambiguous record detected.", instance, matches)
        if primary_key_value:
            primary_match = model.objects.filter(
                **{self.primary_key.name: primary_key_value}
            )
            actual_match = primary_match[0] if primary_match.exists() else None
        else:
            actual_match = None
        if len(matches) == 1:
            if not actual_match:
                raise AmbiguousRecord(
                    f"Primary key did not match record while " "other keys did.",
                    instance,
                    matches,
                )
            if next(iter(matches.values())) != actual_match:
                matches[self.primary_key.verbose_name] = actual_match
                raise AmbiguousRecord(f"Ambiguous record detected.", instance, matches)
        if actual_match:
            if model.compare_instances(actual_match, instance):
                # Identical _instances should be ignored
                raise IdenticalRecord(instance)
            raise CollisionException(actual_match, instance)
        self.__save(instance)

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
        "PL Name",
        "Formula#",
        "Formula factor",
        "ML Shortnames",
        "Rate",
        "Comment",
    ]
    primary_key = Sku._meta.get_field("number")
    model = Sku
    model_name = "SKU"
    _instances = []
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
        "manufacturing_rate": "Rate",
        "comment": "Comment",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sku_mls = []  # list of all SkuManufacturingLine objects to be applied

    def _process_row(
        self, row: Dict[str, Any], filename: str = None, line_num: int = None
    ) -> Dict[str, Any]:
        raw_formula = row["Formula#"]

        formula_qs = Formula.objects.filter(number=raw_formula)
        if formula_qs.exists():
            row["Formula#"] = formula_qs[0]
        else:
            raise IntegrityException(
                message=f"Cannot import SKU #{row['SKU#']}",
                line_num=line_num,
                referring_name="SKU",
                referred_name="Formula",
                fk_name="Formula",
                fk_value=row["Formula#"],
            )
        raw_case_upc = row["Case UPC"]
        if utils.is_valid_upc(raw_case_upc):
            row["Case UPC"] = Upc.objects.get_or_create(upc_number=raw_case_upc)[0]
        else:
            raise UserFacingException(f"{raw_case_upc} is not a valid UPC.")
        raw_unit_upc = row["Unit UPC"]
        if utils.is_valid_upc(raw_unit_upc):
            row["Unit UPC"] = Upc.objects.get_or_create(upc_number=raw_unit_upc)[0]
        else:
            raise UserFacingException(f"{raw_unit_upc} is not a valid UPC.")
        if row["Comment"] is None:
            row["Comment"] = ""
        product_line = ProductLine.objects.filter(name=row["PL Name"])
        if product_line.exists():
            row["PL Name"] = product_line[0]
        else:
            raise IntegrityException(
                message=f"Cannot import SKU #{row['SKU#']}",
                line_num=line_num,
                referring_name="SKU",
                referred_name="Product Line",
                fk_name="PL Name",
                fk_value=row["PL Name"],
            )

        # Duplicated shortnames are ignored
        raw_ml = {
            shortname.strip()
            for shortname in re.split(r",\s*", row["ML Shortnames"])
            if shortname.strip()
        }
        logger.info("Raw ML: %s", raw_ml)
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

        row["ML Shortnames"] = ml_objs.all()
        return row

    def _construct_instance(self, row: Dict[str, Any], line_num: int = None):
        instance = super()._construct_instance(row, line_num)
        [
            self.sku_mls.append(SkuManufacturingLine(sku=instance, line=line))
            for line in row["ML Shortnames"]
        ]

    def _post_process(self):
        pass


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
        "unit": "Unit",  # this column doesn't actually exist
        "comment": "Comment",
    }

    def _process_row(
        self, row: Dict[str, Any], filename: str = None, line_num: int = None
    ) -> Dict[str, Any]:
        raw_size = row["Size"]
        try:
            row["Size"], row["Unit"] = Unit.from_exp(raw_size)
        except RuntimeError as e:
            raise UserFacingException(str(e))
        try:
            row["Size"] = Decimal(row["Size"])
        except InvalidOperation:
            raise UserFacingException(
                f"{row['Size']}is not a valid floating point number"
            )

        vendor = Vendor.objects.filter(info=row["Vendor Info"])
        if vendor.exists():
            row["Vendor Info"] = vendor[0]
        else:
            row["Vendor Info"] = Vendor.objects.create(info=row["Vendor Info"])
        if row["Comment"] is None:
            row["Comment"] = ""
        return row


class FormulaIngredientImporter(Importer):

    file_type = "formulas"
    header = ["Formula#", "Name", "Ingr#", "Quantity", "Comment"]
    field_dict = {
        "formula": "Formula#",
        "ingredient": "Ingr#",
        "quantity": "Quantity",
        "unit": "Unit",
    }
    model = FormulaIngredient
    model_name = "Formula"
    primary_key = FormulaIngredient._meta.get_field("formula")

    def __init__(self, formulas: Dict[str, Formula], filename: str = None):
        super().__init__(filename)
        self.formulas = formulas

    def _process_row(
        self, row: Dict[str, Any], filename: str = None, line_num: int = None
    ) -> Dict[str, Any]:
        raw_size = row["Quantity"]
        try:
            row["Quantity"], row["Unit"] = Unit.from_exp(raw_size)
        except RuntimeError as e:
            raise UserFacingException(str(e))

        row["Formula#"] = self.formulas[row["Name"]]
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
        ingr = ingr[0]
        if row["Unit"].unit_type != ingr.unit.unit_type:
            raise UserFacingException(
                f"Cannot import Formula.\nUnit '{row['Unit'].symbol}' is incompatible "
                f"with unit '{ingr.unit.symbol}' used in ingredient '{ingr.name}'."
            )
        row["Ingr#"] = ingr
        return row

    def _save(self, instance, filename, line_num):
        # We can't save this here because of the special semantics associated with
        # FormulaIngredients. We process all instances together in _post_process.
        return instance

    def _post_process(self):
        FormulaIngredient.objects.filter(formula__in=self.formulas.values()).delete()
        FormulaIngredient.objects.bulk_create(self._instances)


class FormulaImporter(Importer):
    file_type = "formulas"
    header = ["Formula#", "Name", "Ingr#", "Quantity", "Comment"]
    field_dict = {"name": "Name", "number": "Formula#", "comment": "Comment"}
    model = Formula
    model_name = "Formula"
    primary_key = Formula._meta.get_field("number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fi_importer: Optional[FormulaIngredientImporter] = None

    def do_import(self, lines: List[str], filename: str = None):
        lines_copy = copy.copy(lines)
        super_result = super().do_import(lines)
        self.fi_importer = FormulaIngredientImporter(
            formulas={
                instance.name: instance
                for instance in itertools.chain(self.instances, self.ignored)
            },
            filename=filename,
        )
        fi_result = self.fi_importer.do_import(lines_copy)
        return tuple(map(max, zip(super_result, fi_result)))

    def _check_duplicates(
        self,
        raw: Dict[str, str],
        converted: Dict[str, Any],
        filename: str,
        line_num: int,
    ):
        name_value = (raw["Name"],)
        if name_value in self.unique_dict[("name",)]:
            prev_line_num = self.unique_dict[("name",)][name_value]
            if raw["Formula#"]:
                formula_number = (raw["Formula#"],)
                unique_dict = self.unique_dict[("number",)]
                if (
                    formula_number not in unique_dict
                    or unique_dict[formula_number] != prev_line_num
                ):
                    raise UserFacingException(
                        f"Cannot import Formula: formula name '{name_value[0]}' "
                        "and number mismatched. Expected number to match with record "
                        f"in line {prev_line_num}."
                    )
                else:
                    raise Skip
            else:
                raise Skip
        super()._check_duplicates(raw, converted, filename, line_num)

    def commit(self):
        super_commit = super().commit()
        self.fi_importer.commit()
        return super_commit


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
