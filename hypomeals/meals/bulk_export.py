import csv
import logging
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

from django.http import HttpResponse

from meals import utils
from .models import Sku, Ingredient, ProductLine, SkuIngredient

logger = logging.getLogger(__name__)

FILE_TYPE_TO_FIELDS = {
    "skus": {
        "number": "SKU#",
        "name": "Name",
        "case_upc.upc_number": "Case UPC",
        "unit_upc.upc_number": "Unit UPC",
        "unit_size": "Unit size",
        "count": "Count per case",
        "product_line.name": "Product Line Name",
        "comment": "Comment",
    },
    "ingredients": {
        "number": "Ingr#",
        "name": "Name",
        "vendor.info": "Vendor Info",
        "size": "Size",
        "cost": "Cost",
        "comment": "Comment",
    },
    "product_lines": {"name": "Name"},
    "formulas": {
        "sku_number.number": "SKU#",
        "ingredient_number.number": "Ingr#",
        "quantity": "Quantity",
    },
}
FILE_TYPE_TO_FIELDS_REV = {}
for key, value in FILE_TYPE_TO_FIELDS.items():
    FILE_TYPE_TO_FIELDS_REV[key] = {v: k for k, v in value.items()}

HEADERS = {
    "skus": [
        "SKU#",
        "Name",
        "Case UPC",
        "Unit UPC",
        "Unit size",
        "Count per case",
        "Product Line Name",
        "Comment",
    ],
    "ingredients": ["Ingr#", "Name", "Vendor Info", "Size", "Cost", "Comment"],
    "product_lines": ["Name"],
    "formulas": ["SKU#", "Ingr#", "Quantity"],
}

FILE_TYPES = {
    "skus": Sku,
    "ingredients": Ingredient,
    "product_lines": ProductLine,
    "formulas": SkuIngredient,
}

FILE_TYPE_TO_FILENAME = {file_type: f"{file_type}.csv" for file_type in FILE_TYPES}

FILEIFY_THRESHOLD = 200

TEMPDIR = Path(tempfile.gettempdir())

logger = logging.getLogger(__name__)


def _export_objs(stream, file_type, objects):
    """
    Exports a particular type of objects to a CSV file / stream
    :param directory: the directory in which the file will be placed
    :param file_type: the type of file being exported
    :param objects: an iterable of objects to be exported
    :param force_file: if True, a temporary file will always be written. This option
        is used when generating ZIP files for export.
    :return: a (stream, filename) tuple where stream is an IO stream instance pointing
        to the buffer, and filename is a Path to the file written, if one is used, or
        None, if the content of the file is written entirely to memory.
    """
    if file_type not in FILE_TYPES:
        logger.error("Unknown file type '%s'", file_type)
        raise RuntimeError(f"Unknown file type '{file_type}'")

    field_dict = FILE_TYPE_TO_FIELDS_REV[file_type]
    headers = HEADERS[file_type]
    writer = csv.DictWriter(stream, fieldnames=headers)
    writer.writeheader()
    writer.writerows(
        {header: getattr(obj, field_dict[header]) for header in headers}
        for obj in objects
    )
    stream.seek(0)
    return stream


def export_skus(skus, include_formulas=False, include_product_lines=False):
    """
    Exports a list of SKUs, and optionally ZIP up the formulas if the user requested
    that, too.
    :param request: a HttpRequest instance to obtain the session key (as namespace
        for the exported files)
    :param skus: data to be exported
    :param include_formulas: whether to include the formulas for the SKUs. Note that
        this makes the export a ZIP file rather than a CSV file.
    :return: response containing the exported data, either as a CSV or a ZIP file.
    """
    directory = TEMPDIR / utils.make_token_with_timestamp("skus")
    directory.mkdir(parents=True, exist_ok=True)
    logger.info("Will use directory %s", directory)
    sku_file = directory / FILE_TYPE_TO_FILENAME["skus"]
    sku_file.touch(exist_ok=True)
    sku_data = sku_file.open("r+")
    _export_objs(sku_data, "skus", skus)
    logger.info("Exported %d SKU records", len(skus))
    exported_files = [sku_file]
    if include_formulas:
        formulas = SkuIngredient.objects.filter(sku_number__in=skus).order_by(
            "sku_number__number"
        )
        formula_file = directory / FILE_TYPE_TO_FILENAME["formulas"]
        formula_file.touch(exist_ok=True)
        formula_data = formula_file.open("r+")
        _export_objs(formula_data, "formulas", formulas)
        exported_files.append(formula_file)
        logger.info("Exported %d Formula records", len(formulas))

    if include_product_lines:
        product_lines = ProductLine.objects.filter(sku__in=skus).distinct()
        product_line_file = directory / FILE_TYPE_TO_FILENAME["product_lines"]
        product_line_file.touch(exist_ok=True)
        product_line_data = product_line_file.open("r+")
        _export_objs(product_line_data, "product_lines", product_lines)
        exported_files.append(product_line_file)
        logger.info("Exported %d Product Line records", len(product_lines))

    logger.info("exported_files is %s", exported_files)
    if len(exported_files) > 1:
        byte_data = BytesIO()
        with zipfile.ZipFile(byte_data, "w") as zip_file:
            for file in exported_files:
                zip_file.write(file, arcname=file.name)

        response = HttpResponse(byte_data.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = "attachment; filename=archive.zip"
    else:
        response = HttpResponse(exported_files[0].read(), content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=skus.csv"

    return response


def export_ingredients(ingredients):
    """
    Exports a list of ingredients as a temporary CSV file
    :param ingredients: the list of ingredients to be exported
    :return: an HttpResponse containing the exported CSV file
    """
    directory = TEMPDIR / utils.make_token_with_timestamp("ingredients")
    data = _export_objs(directory, "ingredients", ingredients)
    response = HttpResponse(data.read(), content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=ingredients.csv"
    return response
