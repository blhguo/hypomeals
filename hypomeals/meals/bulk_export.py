import csv
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

from django.http import HttpResponse

from .models import Sku, Ingredient, ProductLine, SkuIngredient

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
    "formula": ["SKU#", "Ingr#", "Quantity"],
}

FILE_TYPES = {
    "skus": Sku,
    "ingredients": Ingredient,
    "product_lines": ProductLine,
    "formula": SkuIngredient,
}


def export_formulas(skus):
    """
    Exports a all the formulas associated with a list of SKUs. Each (SKU, Ingredient,
    Quantity) triplet is written to its own line.
    :param skus: List of Sku instances, whose formulas are exported
    :return: the path to a temporary file that contains the CSV content
    """

    tempdir = Path(tempfile.gettempdir())
    file = tempdir / "formulas.csv"
    with open(file, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=HEADERS["formula"])
        writer.writeheader()
        formulas = SkuIngredient.objects.filter(sku_number__in=skus).order_by(
            "sku_number__number"
        )
        writer.writerows(
            {
                "SKU#": formula.sku_number.number,
                "Ingr#": formula.ingredient_number.number,
                "Quantity": formula.quantity,
            }
            for formula in formulas
        )

    return file


def _export_skus(skus):
    """
    Exports a list of SKUs to a CSV file. Each SKU is written to its own line.
    :param skus: List of Sku instances
    :return: the path to a temporary file that contains the CSV content
    """
    tempdir = Path(tempfile.gettempdir())
    file = tempdir / "skus.csv"
    field_dict = FILE_TYPE_TO_FIELDS_REV["skus"]
    with open(file, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=HEADERS["skus"])
        writer.writeheader()
        for sku_object in skus:
            csv_dict = {}
            for header in HEADERS["skus"]:
                csv_dict[header] = getattr(sku_object, field_dict[header])
            writer.writerow(csv_dict)
    return file


def export_skus(skus, include_formulas=False):
    """
    This function asks the two helper functions for csv files, then zips
    :param skus: data to be exported
    :param include_formulas: whether to include the formulas for the SKUs. Note that
        this makes the export a ZIP file rather than a CSV file.
    :return: response containing the exported data, either as a CSV or a ZIP file.
    """
    sku_data = _export_skus(skus)
    if include_formulas:
        formula_data = export_formulas(skus)

        byte_data = BytesIO()
        with zipfile.ZipFile(byte_data, "w") as zip_file:
            zip_file.write(sku_data, arcname=sku_data.name)
            zip_file.write(formula_data, arcname=formula_data.name)

        response = HttpResponse(byte_data.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = "attachment; filename=skus+formulas.zip"
    else:
        with open(sku_data, "rb") as f:
            response = HttpResponse(f.read(), content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=skus.csv"

    return response
