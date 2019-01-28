# pylint: disable-msg=protected-access

import csv
import logging
import os
import os.path
import re
import zipfile

from django.db import transaction, models, IntegrityError

from meals import utils
from meals.exceptions import DuplicateException, IntegrityException, CollisionException
from .models import Sku, SkuIngredient, Upc, ProductLine, Ingredient, Vendor

logger = logging.getLogger(__name__)


FILE_TYPES = {
    "skus": Sku,
    "ingredients": Ingredient,
    "product_lines": ProductLine,
    "formula": SkuIngredient,
}
HEADERS = {
    "skus": "SKU#,Name,Case UPC,Unit UPC,Unit size,"
    "Count per case,Product Line Name,Comment",
    "ingredients": "Ingr#,Name,Vendor Info,Size,Cost,Comment",
    "product_lines": "Name",
    "formula": "SKU#,Ingr#,Quantity",
}
FILE_TYPE_TO_FIELDS = {
    "skus": {
        "number": "SKU#",
        "name": "Name",
        "case_upc": "Case UPC",
        "unit_upc": "Unit UPC",
        "unit_size": "Unit size",
        "count": "Count per case",
        "product_line": "Product Line Name",
        "comment": "Comment",
    },
    "ingredients": {
        "number": "Ingr#",
        "name": "Name",
        "vendor": "Vendor Info",
        "size": "Size",
        "cost": "Cost",
        "comment": "Comment",
    },
    "product_lines": {"name": "Name"},
    "formula": {
        "sku_number": "SKU#",
        "ingredient_number": "Ingr#",
        "quantity": "Quantity",
    },
}
FILE_TYPE_TO_ROW_FUNCTIONS = {}
TOPOLOGICAL_ORDER = ["product_lines", "ingredients", "skus", "formula"]
# A regular expression to parse a Django IntegrityError on duplicate entries
DUPLICATE_ERROR_REGEX = re.compile(
    r"DETAIL:\s*Key\s*\((?P<key>\S+)\)\s*=\s*\((?P<value>\S+)\)"
)


@transaction.atomic
def process_files(csv_files):
    """
    This function does a few things:
    1. it calls a helper function called "process_(type)"
    2. calls check_(type)_integrity() to ensure
        that all relationships exist in the database or in another file
    :param csv_files: a request.FILES dict-like object
    :return: True iff all files are valid, and can be imported
    :raises: DuplicateException: if duplicates are detected within a file
    :raises: IntegrityException: if the files contain invalid references
    """

    file_list = []
    edited = False
    for upload in csv_files.values():
        if re.match(r"(\S)*\.zip", upload.name):
            zf = zipfile.ZipFile(upload)
            names = zf.namelist()
            for name in names:
                file_list.append(zf.open(name))
                edited = True
    if not edited:
        file_list = csv_files.values()
    file_type_dict = {}
    for upload in file_list:
        filename = os.path.basename(upload.name)
        if re.match(r"skus(\S)*\.csv", filename):
            file_type_dict["skus"] = upload
        elif re.match(r"ingredients(\S)*\.csv", filename):
            file_type_dict["ingredients"] = upload
        elif re.match(r"product_lines(\S)*\.csv", filename):
            file_type_dict["product_lines"] = upload
        elif re.match(r"formula(\S)*\.csv", filename):
            file_type_dict["formula"] = upload
        else:
            logger.warning("Ignored unrecognized file: %s", upload.name)

    for file_type in TOPOLOGICAL_ORDER:
        if file_type in file_type_dict:
            name = file_type_dict[file_type]
            logger.info("Processing %s: %s", file_type, name)
            process_file(
                file=name,
                file_type=file_type,
                cls=FILE_TYPES[file_type],
                field_dict=FILE_TYPE_TO_FIELDS[file_type],
            )


def _get_reader(file, file_type):
    header_format = HEADERS[file_type]
    lines = file.read().decode("UTF-8").splitlines()
    if lines[0] == header_format:
        return csv.DictReader(lines)
    logger.error(f"File {file.name} of type {file_type} does not have a valid header")
    raise RuntimeError("Header format mismatch")


def _construct_instance(cls, attr_dict, line_num):
    instance = cls._meta.model()
    for key, value in attr_dict.items():
        setattr(instance, key, value)
    setattr(instance, "line_num", line_num)
    return instance


def _resolve_reference(
    line_num,
    row,
    referring_model_name,
    file_header_name,
    db_name,
    referred_model,
    referred_filename,
):
    value_to_search = row[file_header_name]
    try:
        row[file_header_name] = referred_model.objects.get(**{db_name: value_to_search})
    except referred_model.DoesNotExist as e:
        raise IntegrityException(
            f"Line {line_num}: "
            f"Cannot import '{referring_model_name}' at line {line_num}.",
            referring_name=referring_model_name,
            referred_name=referred_filename,
            fk_name=db_name,
            fk_value=value_to_search,
            raw_exception=e,
        )
    else:
        return row


def _parse_integrity_error(ex):
    match = DUPLICATE_ERROR_REGEX.search(str(ex))
    if match:
        return match.group("key"), match.group("value")
    return None


def _try_save(instance):
    """
    Tries to save a model. If duplicate occurs, check and see if two instances are
    identical: if so, the old instance is returned. Otherwise, raise a
    CollisionException to be handled later.
    :param instance: an instance of the model to be saved
    :return: the saved instance. If an identical record already exists, the previous
        record.
    """
    try:
        instance.save()
    except IntegrityError as e:
        result = _parse_integrity_error(e)
        if result:
            key, value = result
            previous_instance = instance.__class__.objects.get(**{key: value})
            if instance.__class__.compare_instances(instance, previous_instance):
                return previous_instance
            raise CollisionException
        raise e
    else:
        return instance


@utils.register_to_dict(dct=FILE_TYPE_TO_ROW_FUNCTIONS, key="skus")
def _process_sku_row(line_num, row):
    raw_case_upc = row["Case UPC"]
    if True:  # noqa
        # TODO: Add is_valid_upc check
        row["Case UPC"] = Upc.objects.get_or_create(upc_number=raw_case_upc)[0]
    raw_unit_upc = row["Unit UPC"]
    if True:  # noqa
        # TODO: Add is_valid_upc check
        row["Unit UPC"] = Upc.objects.get_or_create(upc_number=raw_unit_upc)[0]
    row = _resolve_reference(
        line_num,
        row,
        referring_model_name="skus",
        file_header_name="Product Line Name",
        db_name="name",
        referred_model=ProductLine,
        referred_filename="product_lines",
    )
    return row


@utils.register_to_dict(dct=FILE_TYPE_TO_ROW_FUNCTIONS, key="ingredients")
def _process_ingredient_row(_, row):
    row["Vendor Info"] = Vendor.objects.create(info=row["Vendor Info"])
    return row


@utils.register_to_dict(dct=FILE_TYPE_TO_ROW_FUNCTIONS, key="formula")
def _process_formula_row(line_num, row):
    row = _resolve_reference(
        line_num,
        row,
        referring_model_name="formula",
        file_header_name="SKU#",
        db_name="number",
        referred_model=Sku,
        referred_filename="skus",
    )
    row = _resolve_reference(
        line_num,
        row,
        referring_model_name="formula",
        file_header_name="Ingr#",
        db_name="number",
        referred_model=Ingredient,
        referred_filename="ingredients",
    )
    return row


def process_file(file, file_type, cls, row_fn=lambda _, x: x, field_dict=None):
    fields = {
        field.name: field
        for field in cls._meta.fields
        if not isinstance(field, models.AutoField)
    }
    if field_dict is None:
        field_dict = {
            field.name: field.name
            for field in fields
            if not isinstance(field, models.AutoField)
        }
    else:
        missing = fields.keys() - field_dict.keys()
        if missing:
            logger.error(
                f"Model {cls._meta.model_name} has {len(fields)} fields but only"
                f" {len(field_dict)} were supplied. Missing={missing}"
            )
            raise RuntimeError("Insufficient fields in field_dict")
    unique_dict = {field.name: {} for field in fields.values() if field.unique}
    reader = _get_reader(file, file_type)
    num_imported = 0
    instances = []
    for line_num, row in enumerate(reader, start=2):
        converted_row = row_fn(line_num, row)
        for unique_key in unique_dict:
            value = converted_row[field_dict[unique_key]]
            if value in unique_dict[unique_key]:
                raise DuplicateException(
                    f"Line {line_num}: "
                    f"Cannot import {file_type} with {unique_key} '{value}'.",
                    model_name=file_type,
                    key=unique_key,
                    value=value,
                    line_num=getattr(unique_dict[unique_key][value], "line_num", -1),
                )
        instance = _construct_instance(
            cls,
            {
                field.name: converted_row[field_dict[field.name]]
                for field in fields.values()
            },
            line_num,
        )
        instance = _try_save(instance)
        instances.append(instance)
        for unique_key in unique_dict:
            unique_dict[unique_key][converted_row[field_dict[unique_key]]] = instance
        num_imported += 1

    logger.info("Imported %d records of model %s", num_imported, cls._meta.model_name)
    return instances


@transaction.atomic
@utils.log_exceptions(logger=logger)
def process_csv_files(files):
    for file_type in TOPOLOGICAL_ORDER:
        if file_type in files:
            file = files[file_type]
            if not file:
                continue
            logger.info("Processing %s: %s", file_type, file)
            params = {
                "file": file,
                "file_type": file_type,
                "cls": FILE_TYPES[file_type],
                "field_dict": FILE_TYPE_TO_FIELDS[file_type],
            }
            if file_type in FILE_TYPE_TO_ROW_FUNCTIONS:
                params["row_fn"] = FILE_TYPE_TO_ROW_FUNCTIONS[file_type]
            process_file(**params)
    return True