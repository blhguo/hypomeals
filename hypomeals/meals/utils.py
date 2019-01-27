import csv
import functools
import os
import os.path
import re
import time
import zipfile

from django.conf import settings
from django.utils import six as django_six
from django.utils.crypto import salted_hmac
from django.utils.deconstruct import deconstructible
from django.utils.http import int_to_base36
from six import string_types

from .models import Sku, SkuIngredient, Upc, ProductLine, Ingredient, Vendor


def process_files(csv_files):
    """
    :param csv_files: FILES uploaded by the user
    (should be a dictionary of form-attributes:file)
    :return: None
    This function calls a helper function called "process_(type)"
    This function then called check_(type)_integrity() to ensure
    that all relationships exist in thedatabase or in another file
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
        tail = os.path.split(upload.name)[1]
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
        and check_product_line_integrity()
        and check_formula_integrity(formula_map, skus_map, ingredients_map)
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
        print(row["Case UPC"])
        case_upc = Upc.objects.get_or_create(upc_number=row["Case UPC"])[0]
        unit_upc = Upc.objects.get_or_create(upc_number=row["Unit UPC"])[0]
        product_line = ProductLine.objects.get_or_create(name=row["Product Line Name"])[
            0
        ]
        created = Sku.objects.get_or_create(
            number=row["SKU#"],
            name=row["Name"],
            case_upc=case_upc,
            unit_upc=unit_upc,
            unit_size=row["Unit size"],
            count=row["Count per case"],
            product_line=product_line,
            comment=row["Comment"],
        )[0]
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
        vendor = Vendor.objects.get_or_create(info=row["Vendor Info"])[0]
        created = Ingredient.objects.get_or_create(
            number=row["Ingr#"],
            name=row["Name"],
            vendor=vendor,
            size=row["Size"],
            cost=row["Cost"],
            comment=row["Comment"],
        )[0]
        if check_ingredient_duplicates(created, ingredients_map):
            created.save()
        else:
            print("Error here")
            # TODO raise DuplicateException(row)
    return ingredients_map


def check_ingredient_duplicates(table_entry, ingredients_map):
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
        created = ProductLine.objects.get_or_create(name=row["Name"])[0]
        if check_product_line_duplicates(created, product_lines_map):
            created.save()
        else:
            print("Error here")
            # TODO raise DuplicateException(row)
    return product_lines_map


def check_product_line_duplicates(table_entry, product_lines_map):
    """
    :param table_entry: The datastructure being checked for duplicates in the database
    :param product_lines_map: The map to which the datastructure will be saved
    :return: boolean representing if a duplicate exists
    """
    ret = True
    if ProductLine.objects.filter(name=table_entry.name).exists():
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
        ing_num = Ingredient.objects.get(number=row["Ingr#"])
        created = SkuIngredient.objects.get_or_create(
            sku_number=sku_num, ingredient_number=ing_num, quantity=row["Quantity"]
        )[0]
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
    for t_model in input_map.values():
        if not (
            Upc.objects.filter(upc_number=t_model.case_upc.upc_number).exists()
            and Upc.objects.filter(upc_number=t_model.unit_upc.upc_number).exists()
            and (
                ProductLine.objects.filter(name=t_model.product_line.name).exists()
                or (t_model.product_line.name in input_map_2.keys())
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
    for t_model in input_map.values():
        if not (Vendor.objects.filter(info=t_model.vendor.info).exists()):
            # TODO: store in bad referential data area
            ret = False
    return ret


def check_product_line_integrity():
    """


    :return: True for now
    """
    return True


def check_formula_integrity(input_map, input_map_2, input_map_3):
    """

    :param input_map: formula_map
    :param input_map_2: Sku_map
    :param input_map_3: Ingredient_map
    :return: Boolean representing if an unfulfilled relationship exists
    """
    ret = True
    for t_model in input_map.values():
        if not (
            (
                Sku.objects.filter(number=t_model.sku_number.number).exists()
                or (t_model.sku_number.number in input_map_2.keys())
            )
            and (
                Ingredient.objects.filter(
                    number=t_model.ingredient_number.number
                ).exists()
                or (t_model.ingredient_number.number in input_map_3.keys())
            )
        ):
            # TODO: store in bad refrential data structure
            ret = False
    return ret


def _make_hash_value(timestamp, *args):
    return "".join(
        [django_six.text_type(arg) for arg in args] + [django_six.text_type(timestamp)]
    )


def make_token_with_timestamp(*args: string_types) -> string_types:
    # timestamp is number of nanoseconds since epoch
    # the last 4 digits should give us enough entropy
    timestamp = int(time.time() * 1e9)
    ts_b36 = int_to_base36(timestamp)[-4:]

    # By hashing on the internal state of the user and using state
    # that is sure to change (the password salt will change as soon as
    # the password is set, at least for current Django auth, and
    # last_login will also change), we produce a hash that will be
    # invalid as soon as it is used.
    # We limit the hash to 20 chars to keep URL short

    key_salt = "HYPOMEALS_TOKEN_GENERATOR"
    secret = settings.SECRET_KEY

    hash_value = salted_hmac(
        key_salt, _make_hash_value(timestamp, *args), secret=secret
    ).hexdigest()[::2]
    return "%s-%s" % (ts_b36, hash_value)


@deconstructible
class UploadToPathAndRename:
    """
    This class is a wrapper around an `upload_to` parameter in, for example, a
    `FileField` of a model. It renames an uploaded file to a secure, time-based token
    generated from an instance's <field_name> attribute (e.g., a name).

    Example use:
    ```
    import utils

    class MyModel(models.Model):

        name = models.CharField(required=True, unique=True, blank=False)

        file = models.FileField(
            upload_to=utils.UploadToPathAndRename("name", "desired/path/"),
            default="desired/path/default",
        )

    ```

    As an example, if an instance of MyModel has name `Test`, id `12345`, and the
    actual filename is `example_file.jpg`, the final uploaded path of the file will be:
    `desired/path/12345-c16o-b6beb44a1fa35a75fe6f.jpg`.
    """

    def __init__(self, field_name, path):
        self.field_name = field_name
        self.sub_path = path

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)
        filename = (
            make_token_with_timestamp(getattr(instance, self.field_name)) + ext[1]
        )
        if instance.pk:
            filename = f"{instance.pk}-{filename}"
        return os.path.join(self.sub_path, filename)


def parameterized(decorator):
    """
    A meta-decorator to make decorators accept parameters.

    Traditionally, in Python, to make a decorator, we simple define a function that
    returns another function. However, the problem arises when the decorator itself,
    rather than the function being decorated, wishes to accept arguments.

    :param decorator: a decorator to decorate
    :return:
    """

    @functools.wraps(decorator)
    def wrapper(*args, **kwargs):
        decorated = functools.wraps(decorator)(
            functools.partial(decorator, *args, **kwargs)
        )
        if args and callable(args[0]):
            return decorated()
        return decorated

    return wrapper


@parameterized
def inject_form_control(func, exclude_names=()):
    """
    Injects the "form-control" class to all widgets in a form.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        for name, field in self.fields.items():
            if name in exclude_names:
                continue
            field.widget.attrs["class"] = (
                field.widget.attrs.get("class", "") + " form-control"
            )

    return wrapper


class BootstrapFormControlMixin:
    """
    Injects the "form-control" class to all widgets bound to a form that inherits from
    this class.
    """

    @classmethod
    def __init_subclass__(cls, **_):

        cls.__init__ = inject_form_control(getattr(cls, "__init__"))
