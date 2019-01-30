import csv
import zipfile
from io import BytesIO

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
FILE_TYPE_TO_FIELDS_REVERSED = {}
for key in FILE_TYPE_TO_FIELDS.keys():
    FILE_TYPE_TO_FIELDS_REVERSED[key] = {v: k for k, v in FILE_TYPE_TO_FIELDS[key].items()}

HEADERS = {
    "skus": ["SKU#","Name", "Case UPC", "Unit UPC", "Unit size",
    "Count per case", "Product Line Name", "Comment"],
    "ingredients": ["Ingr#","Name","Vendor Info","Size","Cost", "Comment"],
    "product_lines": ["Name"],
    "formula": ["SKU#","Ingr#","Quantity"]
}

FILE_TYPES = {
    "skus": Sku,
    "ingredients": Ingredient,
    "product_lines": ProductLine,
    "formula": SkuIngredient,
}

def formula_export(export_data):
    '''
    This function creates a formula csv file from a list of SKUs to export
    :param export_data: List of Sku objects to be exported
    :return: csv file
    '''
    skus_to_export = [getattr(sku, 'number') for sku in export_data]
    myFile = open('formulas_export.csv', 'w')
    field_dict = FILE_TYPE_TO_FIELDS_REVERSED['formula']
    with myFile:
        writer = csv.DictWriter(myFile, fieldnames=HEADERS['formula'])
        writer.writeheader()
        for sku in skus_to_export:
            formula_list = SkuIngredient.objects.filter(sku_number=sku)
            for formula in formula_list:
                csv_dict = {}
                for header in HEADERS['formula']:
                    csv_dict[header] = getattr(formula, field_dict[header])
                writer.writerow(csv_dict)
    return "formulas_export.csv"

def sku_export(export_data):
    '''
    This function creates a Sku csv file from a list of SKUs to export
    :param export_data: List of Sku objects to be exported
    :return: csv file
    '''
    myFile = open('skus_export.csv', 'w')
    field_dict = FILE_TYPE_TO_FIELDS_REVERSED['skus']
    with myFile:
        writer = csv.DictWriter(myFile, fieldnames=HEADERS['skus'])
        writer.writeheader()
        for sku_object in export_data:
            csv_dict = {}
            for header in HEADERS['skus']:
                csv_dict[header] = getattr(sku_object, field_dict[header])
            writer.writerow(csv_dict)
    return 'skus_export.csv'

def process_export(export_data):
    '''
    This function asks the two helper functions for csv files, then zips
    :param export_data: data to be exported
    :return: response containing a zip file
    '''
    sku_data = sku_export(export_data)
    formula_data = formula_export(export_data)
    files = [sku_data, formula_data]

    byte_data = BytesIO()
    zf = zipfile.ZipFile(byte_data, 'w')

    for file in files:
        zf.write(file)
    zf.close()
    response = HttpResponse(byte_data.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=export.zip'

    return response
