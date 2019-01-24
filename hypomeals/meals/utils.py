from django.contrib import messages
import io
import csv
from .models import *
#from django.shortcuts import render


def process_files(request, csv_file):
    keys = ['skus', 'ingr', 'prod', 'sku_']
    sku_map = {}
    ing_map = {}
    prln_map = {}
    qnt_map = {}
    in_map = {'skus': sku_map, 'ingr': ing_map, 'prod': prln_map, 'sku_': qnt_map}
    for upload in csv_file.values():
        process_upload(request, upload, in_map)
    for key in keys:
        if not check_ref_integ(key, in_map):
            #TODO: No actual handling here
            messages.error(request, 'ERROR HAS OCCURRED, REFERENTIAL INTEGRITY LOST')


def process_upload(request, upload, in_map):
    if not upload.name.endswith('.csv'):
        messages.error(request, 'Incorrect file extension')
    datatype = upload.name[0:4]
    data_set = upload.read().decode('UTF-8')
    io_string = io.StringIO(data_set)
    next(io_string)
    if datatype == 'skus':
        for column in csv.reader(io_string, delimiter=',', quotechar="|"):
            case_upc = Upc.objects.get(upc_number=column[2])
            unit_upc = Upc.objects.get(upc_number=column[3])
            product_line = ProductLine.objects.get(name=column[6])
            created = Sku.objects.create(
                number=column[0],
                name=column[1],
                case_upc=case_upc,
                unit_upc=unit_upc,
                unit_size=column[4],
                count=column[5],
                product_line=product_line,
                comment=column[6]
            )
            if check_dupe(created, datatype, in_map):
                created.save()

    if datatype == 'ingr':
        for column in csv.reader(io_string, delimiter=',', quotechar="|"):
            vendor = Vendor.objects.get(info=column[2])
            created = Ingredient.objects.create(
                number=column[0],
                name=column[1],
                vendor=vendor,
                size=column[3],
                cost=column[4],
                comment=column[5]
            )
            if check_dupe(created, datatype, in_map):
                created.save()

    if datatype == 'prod':
        for column in csv.reader(io_string, delimiter=',', quotechar="|"):
            created = ProductLine.objects.create(
                name=column[0]
            )
            if check_dupe(created, datatype, in_map):
                created.save()

    if datatype == 'sku_':
        for column in csv.reader(io_string, delimiter=',', quotechar="|"):
            sku_num = Sku.objects.get(number=column[0])
            ing_num = Ingredient.objects.get(number=column[1])
            created = SkuIngredient.objects.create(
                sku_number=sku_num,
                ingredient_number=ing_num,
                quantity=column[2]
            )
            if check_dupe(created, datatype, in_map):
                created.save()

def check_dupe(table_entry, datatype, in_map):
    d_map = in_map[datatype]
    if datatype == 'skus':
        if not Sku.objects.filter(number=table_entry.number, name=table_entry.name, case_upc=table_entry.case_upc, unit_upc=table_entry.unit_upc, count=table_entry.count, product_line=table_entry.product_line).exists():
            #TODO: Not sure if these should be .number (helpful for Quantiy checking) or .name (helpful for product-line matching)
            d_map[table_entry.number] = table_entry
            return True
    if datatype == 'ingr':
        if not Ingredient.objects.filter(number=table_entry.number, name=table_entry.name, vendor=table_entry.vendor, size=table_entry.size, cost=table_entry.cost).exists():
            d_map[table_entry.number] = table_entry
            return True
    if datatype == 'prod':
        if not ProductLine.objects.filter(name=table_entry.name).exists():
            d_map[table_entry.name] = table_entry
            return True
    if datatype == 'sku_':
        if not SkuIngredient.objects.filter(sku_number=table_entry.sku_number, ingredient_number=table_entry.ingredient_number, quantity=table_entry.quantity).exists():
            #TODO: This defintiely seems rough and should be reviewed (probably wont have key conflicts but its not reall a natural way to create the map
            d_map[len(d_map.keys())] = table_entry
            return True
    return False

def check_ref_integ(datatype, in_map):
    ret = True
    d_map = in_map[datatype]
    for key in d_map.keys():
        t_model = d_map[key]
        if datatype == 'skus':
            if not (Upc.objects.filter(upc_number=t_model.case_upc).exists() and Upc.objects.filter(upc_number=t_model.unit_upc).exists() and ProductLine.objects.filter(name=t_model.product_line).exists()):
                #TODO: store in bad referential data area
                ret = False
        if datatype == 'ingr':
            if not (Vendor.objects.filter(info=t_model.vendor).exists()):
                #TODO: store in bad referential data structure
                ret = False
        if datatype == 'sku_':
            if not (Sku.objects.filter(number=t_model.sku_number).exists() and Ingredient.objects.filter(number=t_model.ingredient_number).exists()):
                #TODO: store in bad refrential data structure
                ret = False
    return ret