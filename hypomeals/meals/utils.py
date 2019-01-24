from django.contrib import messages
import io
import csv
from .models import *


# from django.shortcuts import render


def process_files(request, csv_file):
    """
    :param request: REQUEST object to respond with errors if necessary (error messages currently non-functional)
    :param csv_file: FILES uploaded by the user (should be a dictionary of form-attributes:file)
    :return: None
    This function calls a helper function called "process_upload", who's function is described below.
    This function then called check_ref_integ() to ensure that all relationships exist in the database or in another file
    """
    keys = [
        "skus",
        "ingr",
        "prod",
        "sku_",
    ]  # TODO sku=sku, ingr=ingredients, prod=product line, sku_=Formula
    #TODO I'll change this to be more readable once the import format is set in stone
    sku_map = {}
    ing_map = {}
    prln_map = {}
    qnt_map = {}
    in_map = {
        "skus": sku_map,
        "ingr": ing_map,
        "prod": prln_map,
        "sku_": qnt_map,
    }
    for upload in csv_file.values():
        process_upload(request, upload, in_map)
    for key in keys:
        if not check_referential_integrity(key, in_map):
            # TODO: No actual handling here
            messages.error(
                request,
                "ERROR HAS OCCURRED, REFERENTIAL INTEGRITY LOST",
            )


def process_upload(request, upload, in_map):
    """
    :param request: REQUEST object to respond with errors if necessary (error messages currently non-functional)
    :param upload: One specific FILE uploaded by the user
    :param in_map: Map of Maps. in_map is a String:d_map, and d_map is a map of some identifier (string or number) to DB objects
    :return: None
    This function parses a single CSV file and adds it to the DB.
    It also adds each object (specified by a row in the CSV) to a map for later use to check referential integrity
    """
    if not upload.name.endswith(".csv"):
        messages.error(request, "Incorrect file extension")
    datatype = upload.name[0:4]
    data_set = upload.read().decode("UTF-8")
    io_string = io.StringIO(data_set)
    next(io_string)
    if datatype == "skus":
        for column in csv.reader(
            io_string, delimiter=",", quotechar="|" #TODO: Quotechar might be different, could be '"'
        ):
            case_upc, case_created = Upc.objects.get_or_create(
                upc_number=column[2]
            )
            unit_upc, unit_created = Upc.objects.get_or_create(
                upc_number=column[3]
            )
            product_line, product_line_created = ProductLine.objects.get_or_create(
                name=column[6]
            )
            created, created_bool = Sku.objects.get_or_create(
                number=column[0],
                name=column[1],
                case_upc=case_upc,
                unit_upc=unit_upc,
                unit_size=column[4],
                count=column[5],
                product_line=product_line,
                comment=column[6],
            )
            if not check_duplicates(created, datatype, in_map):
                created.save()
    if datatype == "ingr":
        for column in csv.reader(
            io_string, delimiter=",", quotechar="|"
        ):
            vendor, vendor_created = Vendor.objects.get_or_create(
                info=column[2]
            )
            created, created_bool = Ingredient.objects.get_or_create(
                number=column[0],
                name=column[1],
                vendor=vendor,
                size=column[3],
                cost=column[4],
                comment=column[5],
            )
            if not check_duplicates(created, datatype, in_map):
                created.save()
    if datatype == "prod":
        for column in csv.reader(
            io_string, delimiter=",", quotechar="|"
        ):
            created, created_bool = ProductLine.objects.get_or_create(
                name=column[0]
            )
            if not check_duplicates(created, datatype, in_map):
                created.save()
    if datatype == "sku_":
        for column in csv.reader(
            io_string, delimiter=",", quotechar="|"
        ):
            sku_num = Sku.objects.get(number=column[0])
            ing_num = Ingredient.objects.get(
                number=column[1]
            )
            created, created_bool = SkuIngredient.objects.get_or_create(
                sku_number=sku_num,
                ingredient_number=ing_num,
                quantity=column[2],
            )
            if not check_duplicates(created, datatype, in_map):
                created.save()


def check_duplicates(table_entry, datatype, in_map):
    """
    :param table_entry: One DB object, could be a Sku, Ingredient, Product Line, or Formula
    :param datatype: Specifies if the interpretation should be for Sku, Ingredient, Product Line, or Formula
    :param in_map: Same in_map as before, this function adds things to the in_map for later use
    :return Boolean: representing whether a duplicate exists or not. If duplicate exists, then returns True
    """
    d_map = in_map[datatype]
    ret = True
    if datatype == "skus":
        if not Sku.objects.filter(
            number=table_entry.number,
            name=table_entry.name,
            case_upc=table_entry.case_upc,
            unit_upc=table_entry.unit_upc,
            count=table_entry.count,
            product_line=table_entry.product_line,
        ).exists():
            # TODO: Not sure if these should be .number (helpful for Quantiy checking)
            #  TODO: or .name (helpful for product-line matching)
            d_map[table_entry.number] = table_entry
            ret = False
    if datatype == "ingr":
        if not Ingredient.objects.filter(
            number=table_entry.number,
            name=table_entry.name,
            vendor=table_entry.vendor,
            size=table_entry.size,
            cost=table_entry.cost,
        ).exists():
            d_map[table_entry.number] = table_entry
            ret = False
    if datatype == "prod":
        if not ProductLine.objects.filter(
            name=table_entry.name
        ).exists():
            d_map[table_entry.name] = table_entry
            ret = False
    if datatype == "sku_":
        if not SkuIngredient.objects.filter(
            sku_number=table_entry.sku_number,
            ingredient_number=table_entry.ingredient_number,
            quantity=table_entry.quantity,
        ).exists():
            # TODO: This defintiely seems rough and should be reviewed (probably wont have key conflicts but its not really a natural way to create the map
            d_map[len(d_map.keys())] = table_entry
            ret = False
    return ret


def check_referential_integrity(datatype, in_map):
    """
    :param datatype: String representing what interpretation it should use (Sku, Ingredient, Product Line, or Formula
    :param in_map: Same in_map as before, any relationships in the imported files must exist in either the DB or these maps
    :return: Boolean that is True (if no referential integrity errors occur) and False otherwise
    """
    ret = True
    d_map = in_map[datatype]
    for key, t_model in d_map.items():
        if datatype == "skus":
            if not (
                Upc.objects.filter(
                    upc_number=t_model.case_upc
                ).exists()
                and Upc.objects.filter(
                    upc_number=t_model.unit_upc
                ).exists()
                and ProductLine.objects.filter(
                    name=t_model.product_line
                ).exists()
            ):
                # TODO: store in bad referential data area
                ret = False
        if datatype == "ingr":
            if not (
                Vendor.objects.filter(
                    info=t_model.vendor
                ).exists()
            ):
                # TODO: store in bad referential data structure
                ret = False
        if datatype == "sku_":
            if not (
                Sku.objects.filter(
                    number=t_model.sku_number
                ).exists()
                and Ingredient.objects.filter(
                    number=t_model.ingredient_number
                ).exists()
            ):
                # TODO: store in bad refrential data structure
                ret = False
    return ret
