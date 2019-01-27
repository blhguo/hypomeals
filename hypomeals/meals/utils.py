from django.contrib import messages
import io
import csv
from .models import *
import re
import zipfile
import os.path


# from django.shortcuts import render
def process_files(csv_files):
    """
    :param csv_files: FILES uploaded by the user (should be a dictionary of form-attributes:file)
    :return: None
    This function calls a helper function called "process_(type)", who's function is described below.
    This function then called check_(type)_integrity() to ensure that all relationships exist in the database or in another file
    """
    skus_map = {}
    ingredients_map = {}
    product_line_map = {}
    formula_map = {}
    
    ret = []
    edited = False
    for upload in csv_files.values():
        if re.match(r"(\S)*\.zip", upload.name):
            zf = zipfile.ZipFile(upload)
            names = zf.namelist()
            for name in names:
                ret.append(zf.open(name))
                edited = True
    if not edited:
        ret = csv_files.values()

    for upload in ret:
        head, tail = os.path.split(upload.name)
        if re.match(r"skus(\S)*\.csv", tail):
            skus_map = process_skus(upload)
        elif re.match(r"ingredients(\S)*\.csv", tail):
            ingredients_map = process_ingredients(upload)
        elif re.match(r"product_lines(\S)*\.csv", tail):
            product_line_map = process_product_lines(upload)
        elif re.match(r"formula(\S)*\.csv", tail):
            formula_map = process_formula(upload)
        else:
            print("DOES NOT MATCH")
    if (
        check_sku_integrity(skus_map, product_line_map)
        and check_ingredients_integrity(ingredients_map)
        and check_product_line_integrity(product_line_map)
        and check_formula_integrity(
            formula_map, skus_map, ingredients_map
        )
    ):
        print("Referential Integrity Preserved")
    else:
        print("Referential Integrity Broken")


def process_skus(upload):
    """
    :param upload: The file to be processed, expected to be a csv of SKUs
    :return: A map representing the SKUs created
    """
    temp = upload.read().decode("UTF-8").splitlines()
    reader = csv.DictReader(temp)
    skus_map = {}
    for row in reader:
        print(row['Case UPC'])
        case_upc, case_created = Upc.objects.get_or_create(
            upc_number=row["Case UPC"]
        )
        unit_upc, unit_created = Upc.objects.get_or_create(
            upc_number=row["Unit UPC"]
        )
        product_line, product_line_created = ProductLine.objects.get_or_create(
            name=row["Product Line Name"]
        )
        created, created_bool = Sku.objects.get_or_create(
            number=row["SKU#"],
            name=row["Name"],
            case_upc=case_upc,
            unit_upc=unit_upc,
            unit_size=row["Unit size"],
            count=row["Count per case"],
            product_line=product_line,
            comment=row["Comment"],
        )
        if check_sku_duplicates(created, skus_map):
            print("saving")
            created.save()
        else:
            print("Error here")
            # TODO raise DuplicateException(row)
    return skus_map


def check_sku_duplicates(table_entry, skus_map):
    """
    :param table_entry: The datastructure being checked for duplicates in the database
    :param skus_map: The map to which the datastructure will be saved
    :return: boolean representing if a duplicate exists
    """
    ret = True
    if Sku.objects.filter(
        number=table_entry.number,
        name=table_entry.name,
        case_upc=table_entry.case_upc,
        unit_upc=table_entry.unit_upc,
        count=table_entry.count,
        product_line=table_entry.product_line,
    ).exists():
        ret = False
    else:
        skus_map[table_entry.number] = table_entry
    return ret


def process_ingredients(upload):
    """
    :param upload: File to be processed, expected to be a csv of ingredients
    :return: A map representing the ingredients created
    """
    temp = upload.read().decode("UTF-8").splitlines()
    reader = csv.DictReader(temp)
    ingredients_map = {}
    for row in reader:
        vendor, vendor_created = Vendor.objects.get_or_create(
            info=row["Vendor Info"]
        )
        created, created_bool = Ingredient.objects.get_or_create(
            number=row["Ingr#"],
            name=row["Name"],
            vendor=vendor,
            size=row["Size"],
            cost=row["Cost"],
            comment=row["Comment"],
        )
        if check_ingredient_duplicates(
            created, ingredients_map
        ):
            created.save()
        else:
            print("Error here")
            # TODO raise DuplicateException(row)
    return ingredients_map


def check_ingredient_duplicates(
    table_entry, ingredients_map
):
    """
    :param table_entry: The datastructure being checked for duplicates in the database
    :param ingredients_map: The map to which the datastructure will be saved
    :return: boolean representing if a duplicate exists
    """
    ret = True
    if Ingredient.objects.filter(
        number=table_entry.number,
        name=table_entry.name,
        vendor=table_entry.vendor,
        size=table_entry.size,
        cost=table_entry.cost,
        comment=table_entry.comment,
    ).exists():
        ret = False
    else:
        ingredients_map[table_entry.number] = table_entry
    return ret


def process_product_lines(upload):
    """
    :param upload: File to be processed, expected to be a csv of Product lines
    :return: A map representing the Product Lines created
    """
    temp = upload.read().decode("UTF-8").splitlines()
    reader = csv.DictReader(temp)
    product_lines_map = {}
    for row in reader:
        created, created_bool = ProductLine.objects.get_or_create(
            name=row["Name"]
        )
        if check_product_line_duplicates(
            created, product_lines_map
        ):
            created.save()
        else:
            print("Error here")
            # TODO raise DuplicateException(row)
    return product_lines_map


def check_product_line_duplicates(
    table_entry, product_lines_map
):
    """
    :param table_entry: The datastructure being checked for duplicates in the database
    :param product_lines_map: The map to which the datastructure will be saved
    :return: boolean representing if a duplicate exists
    """
    ret = True
    if ProductLine.objects.filter(
        name=table_entry.name
    ).exists():
        ret = False
    else:
        product_lines_map[table_entry.number] = table_entry
    return ret


def process_formula(upload):
    """
    :param upload: File to be processed, expected to be a csv of formulas
    :return: A map representing the formulas created
    """
    temp = upload.read().decode("UTF-8").splitlines()
    reader = csv.DictReader(temp)
    formula_map = {}
    for row in reader:
        sku_num = Sku.objects.get(number=row["SKU#"])
        ing_num = Ingredient.objects.get(
            number=row["Ingr#"]
        )
        created, created_bool = SkuIngredient.objects.get_or_create(
            sku_number=sku_num,
            ingredient_number=ing_num,
            quantity=row["Quantity"],
        )
        if check_formula_duplicates(created, formula_map):
            created.save()
        else:
            print("Error here")
            # TODO raise DuplicateException(row)
    return formula_map


def check_formula_duplicates(table_entry, formula_map):
    """
    :param table_entry: The datastructure being checked for duplicates in the database
    :param formula_map: The map to which the datastructure will be saved
    :return: boolean representing if a duplicate exists
    """
    ret = True
    # TODO: Update models to be formula
    if not SkuIngredient.objects.filter(
        sku_number=table_entry.sku_number,
        ingredient_number=table_entry.ingredient_number,
        quantity=table_entry.quantity,
    ).exists():
        ret = False
    else:
        formula_map[table_entry.__str__()] = table_entry
    return ret


def check_sku_integrity(input_map, input_map_2):
    """

    :param input_map: Sku_map
    :param input_map_2: Product_line_map
    :return: Boolean representing whether an unfulfilled relationship exists
    """
    ret = True
    for index, t_model in input_map.items():
        if not (
            Upc.objects.filter(
                upc_number=t_model.case_upc.upc_number
            ).exists()
            and Upc.objects.filter(
                upc_number=t_model.unit_upc.upc_number
            ).exists()
            and (
                ProductLine.objects.filter(
                    name=t_model.product_line.name
                ).exists()
                or (
                    t_model.product_line.name
                    in input_map_2.keys()
                )
            )
        ):
            # TODO: store in bad referential data area
            ret = False
    return ret


def check_ingredients_integrity(input_map):
    """

    :param input_map: Ingredients_map
    :return: Boolean representing whether an unfulfilled relationship exists
    """
    ret = True
    for index, t_model in input_map.items():
        if not (
            Vendor.objects.filter(
                info=t_model.vendor.info
            ).exists()
        ):
            # TODO: store in bad referential data area
            ret = False
    return ret


def check_product_line_integrity(input_map):
    """

    :param input_map: Product_line_map, added in case later erferential integrity checks need to be done
    :return: True for now
    """
    return True


def check_formula_integrity(
    input_map, input_map_2, input_map_3
):
    """

    :param input_map: formula_map
    :param input_map_2: Sku_map
    :param input_map_3: Ingredient_map
    :return: Boolean representing if an unfulfilled relationship exists
    """
    ret = True
    for index, t_model in input_map.items():
        if not (
            (
                Sku.objects.filter(
                    number=t_model.sku_number.number
                ).exists()
                or (
                    t_model.sku_number.number
                    in input_map_2.keys()
                )
            )
            and (
                Ingredient.objects.filter(
                    number=t_model.ingredient_number.number
                ).exists()
                or (
                    t_model.ingredient_number.number
                    in input_map_3.keys()
                )
            )
        ):
            # TODO: store in bad refrential data structure
            ret = False
    return ret
