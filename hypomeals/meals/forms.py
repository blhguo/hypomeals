# pylint: disable-msg=protected-access
import logging
import re
import zipfile
from collections import OrderedDict, defaultdict
from pathlib import Path

from django import forms
from django.contrib.auth.models import Group
from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, BLANK_CHOICE_DASH
from django.forms import formset_factory
from django.urls import reverse_lazy

from meals import bulk_import
from meals import utils
from meals.constants import ADMINS_GROUP, USERS_GROUP
from meals.exceptions import CollisionOccurredException
from meals.models import (
    FormulaIngredient,
    SkuManufacturingLine,
    ManufacturingLine,
    Formula,
    Goal,
    GoalSchedule,
    User,
    Sku,
    Ingredient,
    ProductLine,
    Upc,
    Vendor,
    Unit,
)
from meals.utils import BootstrapFormControlMixin, FilenameRegexValidator

logger = logging.getLogger(__name__)

COMMA_SPLIT_REGEX = re.compile(r",\s*")


class AutocompletedCharField(forms.CharField):
    """
    An CharField with autocomplete built-in.

    This is nothing fancy. It simply adds the class "meals-autocomplete" to and an
    extra attribute "data-autocomplete-url" to the input element, which are then used
    by a hook in common.js to register autocomplete.

    For example, to register an multiple field for ingredient names,
    >>> from django.urls import reverse
    >>> class MyForm(forms.Form):
    ...     ingr = AutocompletedCharField(
    ...         data_source=reverse("autocomplete-ingredient"),
    ...         is_multiple=True,
    ...     )
    :param data_source: the url of an autocomplete view.
    """

    def __init__(self, *args, data_source, is_multiple=False, **kwargs):
        self.data_source = data_source
        self.is_multiple = is_multiple
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs["class"] = attrs.get("class", "") + " meals-autocomplete"
        attrs["data-autocomplete-url"] = self.data_source
        if self.is_multiple:
            attrs["class"] += " meals-autocomplete-multiple"
        return attrs


class ImportForm(forms.Form, BootstrapFormControlMixin):
    skus = forms.FileField(
        required=False,
        label="SKU",
        validators=[
            FilenameRegexValidator(
                regex=r".*skus(\S)*\.csv",
                message="Filename mismatch. Expected: "
                "skusxxx.csv where xxx is any characters.",
                code="filename-mismatch",
            )
        ],
    )
    ingredients = forms.FileField(
        required=False,
        label="Ingredients",
        validators=[
            FilenameRegexValidator(
                regex=r".*ingredients(\S)*\.csv",
                message="Filename mismatch. Expected: "
                "ingredientsxxx.csv where xxx is any characters.",
                code="filename-mismatch",
            )
        ],
    )
    product_lines = forms.FileField(
        required=False,
        label="Product Lines",
        validators=[
            FilenameRegexValidator(
                regex=r".*product_lines(\S)*\.csv",
                message="Filename mismatch. Expected: "
                "product_linesxxx.csv where xxx is any characters.",
                code="filename-mismatch",
            )
        ],
    )
    formulas = forms.FileField(
        required=False,
        label="Formulas",
        validators=[
            FilenameRegexValidator(
                regex=r".*formulas(\S)*\.csv",
                message="Filename mismatch. Expected: "
                "formulaxxx.csv where xxx is any characters.",
                code="filename-mismatch",
            )
        ],
    )

    zip = forms.FileField(required=False, label="ZIP File")

    def __init__(self, *args, session_key, **kwargs):
        self._imported = False
        self.session_key = session_key
        super().__init__(*args, **kwargs)

    def _unzip(self):
        zip_file = zipfile.ZipFile(self.cleaned_data["zip"])
        names = zip_file.namelist()
        csv_files = {}
        for path in names:
            name = Path(path).name
            if re.match(r"skus(\S)*\.csv", name):
                file = File(file=zip_file.open(path), name=name)
                csv_files["skus"] = file
                logger.info("Matched file %s for skus", path)
            elif re.match(r"ingredients(\S)*\.csv", name):
                file = File(file=zip_file.open(path), name=name)
                csv_files["ingredients"] = file
                logger.info("Matched file %s for ingredients", path)
            elif re.match(r"product_lines(\S)*\.csv", name):
                file = File(file=zip_file.open(path), name=name)
                csv_files["product_lines"] = file
                logger.info("Matched file %s for product_lines", path)
            elif re.match(r"formula(\S)*\.csv", name):
                file = File(file=zip_file.open(path), name=name)
                csv_files["formulas"] = file
                logger.info("Matched file %s for formulas", path)
            else:
                logger.warning("Ignored unrecognized path: %s", path)
        return csv_files

    def clean(self):
        if not any(self.cleaned_data.values()):
            raise ValidationError(
                "You must upload at least one CSV file or a ZIP file. "
                "Make sure the filenames are correct."
            )
        csv_files = {}
        for file_type, file in self.cleaned_data.items():
            if file_type != "zip":
                csv_files[file_type] = file
        if self.cleaned_data["zip"]:
            if any(csv_files.values()):
                raise ValidationError(
                    "You can either submit individual CSV files, or a single ZIP file, "
                    "but not both."
                )

            csv_files = self._unzip()
        try:
            inserted = bulk_import.process_csv_files(csv_files, self.session_key)
            if inserted:
                self._imported = True
        except CollisionOccurredException:
            raise
        except Exception as e:
            raise ValidationError(str(e))

        return inserted

    @property
    def imported(self):
        return self._imported


def get_ingredient_choices():
    return [(ing.number, ing.name) for ing in Ingredient.objects.all()]


def get_product_line_choices():
    return [(pl.name, pl.name) for pl in ProductLine.objects.all()]


def get_manufacturing_line_choices():
    return [(pl.name, pl.name) for pl in ManufacturingLine.objects.all()]


def get_formula_choices():
    return [(pl.name, pl.name) for pl in Formula.objects.all()]


def get_vendor_choices():
    return [(ven.info, ven.info) for ven in Vendor.objects.all()]


def get_sku_choices():
    return [(sku.number, sku.number) for sku in Sku.objects.all()]


def get_unit_choices(unit_type=None):
    if unit_type is None:
        return [
            (un.symbol, f"{un.symbol} ({un.verbose_name})") for un in Unit.objects.all()
        ]
    return [
        (un.symbol, f"{un.symbol} ({un.verbose_name})")
        for un in Unit.objects.filter(unit_type=unit_type)
    ]


class CsvAutocompletedField(AutocompletedCharField):
    attr = "pk"

    def __init__(self, model, *args, attr, data_source, return_qs=False, **kwargs):
        """
        Constructs a new instance of CsvAutocompletedField
        :param model: the model to search for matches
        :param attr: the attribute on the model to search for matches
        :param data_source: an autocomplete data source. See AutocompletedCharField
        :param return_qs: if True, the raw queryset (rather than the matches strings),
            will be returned in the clean() method.
        """
        super().__init__(*args, data_source=data_source, is_multiple=True, **kwargs)
        try:
            model._meta.get_field(attr)
        except FieldDoesNotExist:
            raise AssertionError(
                f"Model '{model._meta.model_name}' has no attribute '{attr}'"
            )
        self.model = model
        self.attr = attr
        self.return_qs = return_qs

    def clean(self, value):
        # Get rid of any empty values
        items = {item.strip() for item in COMMA_SPLIT_REGEX.split(value)} - {""}
        if not items:
            return items
        query = Q(**{f"{self.attr}__in": items})
        qs = self.model.objects.filter(query)
        found = set(qs.values_list(self.attr, flat=True))
        not_found = items - found
        if not_found:
            errors = []
            for item in not_found:
                errors.append(
                    ValidationError(
                        "'%(item)s' cannot be found.", params={"item": item}
                    )
                )
            raise ValidationError(errors)
        return qs if self.return_qs else found


class SkuAutocompletedField(CsvAutocompletedField):
    def clean(self, value):
        items = {item.strip() for item in COMMA_SPLIT_REGEX.split(value)} - {""}
        if not items:
            return items
        results = []
        for item in items:
            sku = Sku.from_name(item)
            if sku is None:
                raise ValidationError(
                    "'%(item)s' cannot be found.", params={"item": item}
                )
            results.append(sku)
        return results if self.return_qs else items


class EditProductLineForm(forms.ModelForm):
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Enter a new name..."}),
        help_text="Note that this field is case sensitive!",
    )

    class Meta:
        model = ProductLine
        fields = ["name"]
        help_texts = {"name": "Name of the new Product Line"}

    def __init__(self, *args, **kwargs):
        initial = {}
        if "instance" in kwargs:
            instance = kwargs["instance"]
            if hasattr(instance, "pk") and instance.pk:
                initial.update({"name": instance.name})
        super().__init__(*args, initial=initial, **kwargs)
        reordered_fields = OrderedDict()
        for field_name in self.Meta.fields:
            if field_name in self.fields:
                reordered_fields[field_name] = self.fields[field_name]
                reordered_fields[field_name].widget.attrs["class"] = "form-control"
        self.fields = reordered_fields

    def clean(self):
        # The main thing to check for here is whether the user has supplied a custom
        # Product Line, if "Custom" was chosen in the dropdown
        data = super().clean()
        if "name" in data:
            if data["name"] is None:
                raise ValidationError("You must specify a name")
        return data

    @transaction.atomic
    def save(self, commit=False):
        instance = super().save(commit)
        # Manually save the foreign keys, then attach them to the instance
        fks = []
        for fk in fks:
            self.cleaned_data[fk].save()
            setattr(instance, fk, self.cleaned_data[fk])
        instance.save()
        self.save_m2m()
        return instance


class IngredientFilterForm(forms.Form):
    NUM_PER_PAGE_CHOICES = [(i, str(i)) for i in range(50, 501, 50)] + [(-1, "All")]

    page_num = forms.IntegerField(
        widget=forms.HiddenInput(), initial=1, min_value=1, required=False
    )
    num_per_page = forms.ChoiceField(choices=NUM_PER_PAGE_CHOICES, required=True)
    sort_by = forms.ChoiceField(choices=Ingredient.get_sortable_fields, required=True)
    keyword = forms.CharField(required=False, max_length=100)
    skus = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Start typing..."}),
        help_text="Enter ingredients separated by commas",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control mb-2"

    def clean_skus(self):
        value = self.cleaned_data["skus"]
        items = {item.strip() for item in COMMA_SPLIT_REGEX.split(value)} - {""}
        if not items:
            return items
        found = set()
        not_found = []
        for item in items:
            sku = Sku.from_name(item)
            if sku is None:
                not_found.append(item)
            else:
                found.add(sku)
        if not_found:
            errors = []
            for item in not_found:
                errors.append(
                    ValidationError(
                        "'%(item)s' cannot be found.", params={"item": item}
                    )
                )
            raise ValidationError(errors)
        return found

    def query(self) -> Paginator:
        params = self.cleaned_data
        logger.info("Querying ingredients with parameters %s", params)
        num_per_page = int(params.get("num_per_page", 50))
        sort_by = params.get("sort_by", "")
        query_filter = Q()
        if params["keyword"]:
            query_filter &= Q(name__icontains=params["keyword"]) | Q(
                number__icontains=params["keyword"]
            )
        if params["skus"]:
            query_filter |= Q(sku__in=params["skus"])
        query = Ingredient.objects.filter(query_filter)
        if sort_by:
            query = query.order_by(sort_by)
        if num_per_page == -1:
            num_per_page = query.count()
        return Paginator(query.distinct(), num_per_page)


class FormulaFilterForm(forms.Form):
    NUM_PER_PAGE_CHOICES = [(i, str(i)) for i in range(50, 501, 50)] + [(-1, "All")]

    page_num = forms.IntegerField(
        widget=forms.HiddenInput(), initial=1, min_value=1, required=False
    )
    num_per_page = forms.ChoiceField(choices=NUM_PER_PAGE_CHOICES, required=True)
    sort_by = forms.ChoiceField(choices=Formula.get_sortable_fields, required=True)
    keyword = forms.CharField(required=False, max_length=100)
    ingredients = CsvAutocompletedField(
        model=Ingredient,
        data_source=reverse_lazy("autocomplete_ingredients"),
        attr="name",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Start typing..."}),
        help_text="Enter ingredients separated by commas",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control mb-2"

    def query(self) -> Paginator:
        params = self.cleaned_data
        logger.info("Querying ingredients with parameters %s", params)
        num_per_page = int(params.get("num_per_page", 50))
        sort_by = params.get("sort_by", "")
        query_filter = Q()
        if params["keyword"]:
            query_filter &= Q(name__icontains=params["keyword"]) | Q(
                number__icontains=params["keyword"]
            )
        if params["ingredients"]:
            query_filter &= Q(
                formulaingredient__ingredient__name__in=params["ingredients"]
            )
        query = Formula.objects.filter(query_filter)
        if sort_by:
            query = query.order_by(sort_by)
        if num_per_page == -1:
            num_per_page = query.count()
        print("TEST", query)
        return Paginator(query.distinct(), num_per_page)


class EditIngredientForm(forms.ModelForm):
    custom_vendor = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter a new vendor..."}),
        help_text="Note that this field is case sensitive!",
    )
    vendor = forms.ChoiceField(
        choices=lambda: BLANK_CHOICE_DASH
        + [("custom", "Custom")]
        + get_vendor_choices(),
        required=True,
    )

    unit = forms.ChoiceField(
        choices=lambda: BLANK_CHOICE_DASH + get_unit_choices(), required=True
    )

    class Meta:
        model = Ingredient
        fields = [
            "name",
            "number",
            "vendor",
            "custom_vendor",
            "size",
            "unit",
            "cost",
            "comment",
        ]
        exclude = ["vendor"]
        widgets = {"comment": forms.Textarea(attrs={"maxlength": 4000})}
        labels = {"number": "Ingr#"}
        help_texts = {
            "name": "Name of the new Ingredient.",
            "number": "An alphanumeric identifier for this new SKU. "
            "If empty, one will be autogenerated.",
        }

    def __init__(self, *args, **kwargs):
        initial = {}
        if "instance" in kwargs:
            instance = kwargs["instance"]
            if hasattr(instance, "pk") and instance.pk:
                initial.update({"vendor": instance.vendor.info})
                initial.update({"unit": instance.unit.symbol})
        super().__init__(*args, initial=initial, **kwargs)
        reordered_fields = OrderedDict()
        for field_name in self.Meta.fields:
            if field_name in self.fields:
                reordered_fields[field_name] = self.fields[field_name]
                reordered_fields[field_name].widget.attrs["class"] = "form-control"
        self.fields = reordered_fields

        self.fields["number"].required = False

        if "instance" in kwargs:
            instance = kwargs["instance"]
            if hasattr(instance, "pk") and instance.pk:
                self.fields["number"].disabled = True
                self.fields["unit"] = forms.ChoiceField(
                    choices=get_unit_choices(unit_type=instance.unit.unit_type),
                    required=True,
                )
                self.fields["unit"].widget.attrs.update({"class": "form-control"})

    def clean(self):
        # The main thing to check for here is whether the user has supplied a custom
        # Vendor, if "Custom" was chosen in the dropdown
        data = super().clean()
        if "vendor" in data:
            if data["vendor"] == "custom":
                if "custom_vendor" not in data or not data["custom_vendor"]:
                    raise ValidationError(
                        "You must specify a custom Vendor, or choose "
                        "from an existing Vendor."
                    )
                data["vendor"] = data["custom_vendor"]
            qs = Vendor.objects.filter(info=data["vendor"])
            data["vendor"] = qs[0] if qs.exists() else Vendor(info=data["vendor"])
        if "unit" not in data or not Unit.objects.filter(symbol=data["unit"]).exists():
            raise ValidationError("You must specify a Unit")
        else:
            data["unit"] = Unit.objects.filter(symbol=data["unit"])[0]

        return data

    @transaction.atomic
    def save(self, commit=False):
        instance = super().save(commit)
        # Manually save the foreign keys, then attach them to the instance
        fks = ["vendor", "unit"]
        for fk in fks:
            self.cleaned_data[fk].save()
            setattr(instance, fk, self.cleaned_data[fk])
        instance.save()
        self.save_m2m()
        return instance


class SkuFilterForm(forms.Form, utils.BootstrapFormControlMixin):
    NUM_PER_PAGE_CHOICES = [(i, str(i)) for i in range(50, 501, 50)] + [(-1, "All")]

    page_num = forms.IntegerField(
        widget=forms.HiddenInput(), initial=1, min_value=1, required=False
    )
    num_per_page = forms.ChoiceField(choices=NUM_PER_PAGE_CHOICES, required=True)
    sort_by = forms.ChoiceField(choices=Sku.get_sortable_fields, required=True)
    keyword = forms.CharField(required=False, max_length=100)
    ingredients = CsvAutocompletedField(
        model=Ingredient,
        data_source=reverse_lazy("autocomplete_ingredients"),
        required=False,
        attr="name",
        help_text="Enter ingredients separated by commas",
    )
    product_lines = CsvAutocompletedField(
        model=ProductLine,
        required=False,
        attr="name",
        data_source=reverse_lazy("autocomplete_product_lines"),
        help_text="Enter Product Lines separated by commas",
    )
    formulas = CsvAutocompletedField(
        model=Formula,
        data_source=reverse_lazy("autocomplete_formulas"),
        required=False,
        attr="name",
        help_text="Enter formulas separated by commas",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["ingredients"].widget.attrs["placeholder"] = "Start typing..."
        self.fields["product_lines"].widget.attrs["placeholder"] = "Start typing..."
        self.fields["formulas"].widget.attrs["placeholder"] = "Start typing..."

    def add_formula_name(self, name):
        self.cleaned_data["formulas"] = name

    def query(self) -> Paginator:
        # Generate the correct query, execute it, and return the requested page.
        # Requirement 2.3.2.1
        # Modified according to https://piazza.com/class/jpvlvyxg51d1nc?cid=40
        params = self.cleaned_data
        num_per_page = int(params.get("num_per_page", 50))
        sort_by = params.get("sort_by", "")
        query_filter = Q()
        if params["keyword"]:
            query_filter &= (
                Q(name__icontains=params["keyword"])
                | Q(number__icontains=params["keyword"])
                | Q(unit_upc__upc_number__icontains=params["keyword"])
                | Q(case_upc__upc_number__icontains=params["keyword"])
            )
        if params["ingredients"]:
            query_filter &= Q(formula__ingredients__name__in=params["ingredients"])
        if params["product_lines"]:
            query_filter &= Q(product_line__name__in=params["product_lines"])
        if params["formulas"]:
            query_filter &= Q(formula__name__in=params["formulas"])
        query = Sku.objects.filter(query_filter)
        if sort_by:
            query = query.order_by(sort_by)
        if num_per_page == -1:
            num_per_page = query.count()
        return Paginator(query.distinct(), num_per_page)


class UpcField(forms.CharField):
    max_length = 12
    min_length = 12

    def clean(self, value):
        value = str(super().clean(value))
        # add 0 if number is less than 12 digits
        value = "0" * (12 - len(value)) + value
        if utils.is_valid_upc(value):
            if value[0] not in ["2", "3", "4", "5"]:
                return value
            raise ValidationError(
                "%(value)s does not represent a consumer product",
                params={"value": value}
            )
        raise ValidationError(
            "%(value)s is not a valid UPC number", params={"value": value}
        )


class EditSkuForm(forms.ModelForm, utils.BootstrapFormControlMixin):
    case_upc = UpcField(
        label="Case UPC#", widget=forms.NumberInput(attrs={"maxlength": 12})
    )
    unit_upc = UpcField(
        label="Unit UPC#", widget=forms.NumberInput(attrs={"maxlength": 12})
    )
    custom_product_line = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter a new product line..."}),
        help_text="Note that this field is case sensitive!",
    )
    product_line = forms.ChoiceField(
        choices=lambda: BLANK_CHOICE_DASH
        + [("custom", "Custom")]
        + get_product_line_choices(),
        required=True,
    )
    formula = forms.ChoiceField(
        choices=lambda: BLANK_CHOICE_DASH + get_formula_choices(), required=True
    )
    manufacturing_lines = CsvAutocompletedField(
        model=ManufacturingLine,
        data_source=reverse_lazy("autocomplete_manufacturing_lines"),
        required=True,
        attr="shortname",
        help_text="Enter Manufacturing Lines separated by commas",
    )

    class Meta:
        model = Sku
        fields = [
            "name",
            "number",
            "case_upc",
            "unit_upc",
            "unit_size",
            "count",
            "product_line",
            "custom_product_line",
            "comment",
            "formula",
            "formula_scale",
            "manufacturing_lines",
            "manufacturing_rate",
        ]
        exclude = [
            "case_upc",
            "unit_upc",
            "product_line",
            "formula",
            "manufacturing_lines",
        ]
        widgets = {"comment": forms.Textarea(attrs={"maxlength": 4000})}
        labels = {"number": "SKU#"}
        help_texts = {
            "name": "Name of the new SKU.",
            "number": "A numeric identifier for this new SKU."
            " If empty, one will be autogenerated.",
        }

    def __init__(self, *args, **kwargs):
        initial = kwargs.pop("initial") if "initial" in kwargs else {}
        if "instance" in kwargs:
            instance = kwargs["instance"]
            if hasattr(instance, "pk") and instance.pk:
                sku_manufacturing_lines = SkuManufacturingLine.objects.filter(
                    sku=instance
                )
                manufacturing_lines = ", ".join(
                    [instance.line.shortname for instance in sku_manufacturing_lines]
                )
                initial.update(
                    {
                        "case_upc": instance.case_upc.upc_number,
                        "unit_upc": instance.unit_upc.upc_number,
                        "product_line": instance.product_line.name,
                        "formula": instance.formula.name,
                        "manufacturing_lines": manufacturing_lines,
                    }
                )
        super().__init__(*args, initial=initial, **kwargs)
        reordered_fields = OrderedDict()
        for field_name in self.Meta.fields:
            if field_name in self.fields:
                reordered_fields[field_name] = self.fields[field_name]
        self.fields = reordered_fields

        self.fields["number"].required = False

        if "instance" in kwargs:
            instance = kwargs["instance"]
            if hasattr(instance, "pk") and instance.pk:
                self.fields["number"].disabled = True

    def clean_case_upc(self):
        upc = self.cleaned_data["case_upc"]
        sku = Sku.objects.filter(case_upc__upc_number=upc)
        if sku.exists() and sku[0] != self.instance:
            raise ValidationError(
                "An SKU with Case UPC #%(case_upc)s "
                "already exists. Old SKU is #%(sku)d",
                params={"case_upc": upc, "sku": sku[0].pk},
            )
        return Upc.objects.get_or_create(upc_number=upc)[0]

    def clean_unit_upc(self):
        upc = self.cleaned_data["unit_upc"]
        try:
            return Upc.objects.get(upc_number=upc)
        except Upc.DoesNotExist:
            return Upc(upc_number=upc)

    def clean(self):
        # The main thing to check for here is whether the user has supplied a custom
        # Product Line, if "Custom" was chosen in the dropdown
        data = super().clean()
        if "product_line" in data:
            if data["product_line"] == "custom":
                if "custom_product_line" not in data or not data["custom_product_line"]:
                    raise ValidationError(
                        "You must specify a custom Product Line, or choose "
                        "from an existing Product Line."
                    )
                data["product_line"] = data["custom_product_line"]
            try:
                data["product_line"] = ProductLine.objects.get(
                    name=data["product_line"]
                )
            except ProductLine.DoesNotExist:
                data["product_line"] = ProductLine(name=data["product_line"])
        ### Remember to Solve the Inline Editing Latter
        if "formula" in data:
            try:
                data["formula"] = Formula.objects.get(name=data["formula"])
            except Formula.DoesNotExist:
                data["formula"] = Formula(name=data["formula"])

        if "manufacturing_lines" in data:
            manufacturing_lines = self.cleaned_data["manufacturing_lines"]
            manufacturing_lines_objs = []
            for manufacturing_line in manufacturing_lines:
                try:
                    manufacturing_line_obj = ManufacturingLine.objects.get(
                        shortname=manufacturing_line
                    )
                    manufacturing_lines_objs.append(manufacturing_line_obj)
                except ManufacturingLine.DoesNotExist:
                    error_message = (
                        "Manufactuing Line with Short Name: %s doesn't exist"
                        % (manufacturing_line,)
                    )
                    self.add_error(
                        self.cleaned_data["manufacturing_line"], error_message
                    )
            data["manufacturing_lines"] = manufacturing_lines_objs

        return data

    @transaction.atomic
    def save(self, commit=False):
        instance = super().save(commit)
        # Manually save the foreign keys, then attach them to the instance
        fks = ["case_upc", "unit_upc", "product_line", "formula"]
        for fk in fks:
            self.cleaned_data[fk].save()
            setattr(instance, fk, self.cleaned_data[fk])
        manufacturing_lines = self.cleaned_data["manufacturing_lines"]
        SkuManufacturingLine.objects.filter(sku=instance).delete()
        instance.save()
        for manufacturing_line in manufacturing_lines:
            SkuManufacturingLine.objects.create(sku=instance, line=manufacturing_line)
        self.save_m2m()
        return instance


class ManufacturingLineForm(forms.ModelForm, utils.BootstrapFormControlMixin):

    skus = SkuAutocompletedField(
        Sku,
        data_source=reverse_lazy("autocomplete_skus"),
        attr="name",
        return_qs=True,
        required=False,
        label="SKUs",
        help_text="Optionally specify a comma-separated list of SKUs that "
        "this manufacturing line produces.",
        widget=forms.TextInput(attrs={"placeholder": "Start typing..."}),
    )
    comment = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"maxlength": 4000})
    )

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        initial = kwargs.pop("initial", {})
        if instance:
            initial["skus"] = ", ".join(
                line.sku.verbose_name for line in instance.skus.all()
            )
        super().__init__(*args, instance=instance, initial=initial, **kwargs)

    @transaction.atomic
    def save(self, commit=False):
        instance = super().save(commit=commit)
        sku_line_objs = []
        if self.cleaned_data["skus"]:
            sku_line_objs = [
                SkuManufacturingLine(sku=sku, line=instance)
                for sku in self.cleaned_data["skus"]
            ]
            if commit:
                SkuManufacturingLine.objects.filter(line=instance).delete()
                SkuManufacturingLine.objects.bulk_create(sku_line_objs)
        return instance, sku_line_objs

    class Meta:
        model = ManufacturingLine
        fields = ["name", "shortname", "comment"]


class FormulaNameForm(forms.ModelForm, utils.BootstrapFormControlMixin):
    def __init__(self, *args, **kwargs):
        initial = kwargs.pop("initial") if "initial" in kwargs else {}
        super().__init__(*args, initial=initial, **kwargs)
        reordered_fields = OrderedDict()
        for field_name in self.Meta.fields:
            if field_name in self.fields:
                reordered_fields[field_name] = self.fields[field_name]
                reordered_fields[field_name].widget.attrs["class"] = "form-control"
        self.fields = reordered_fields

        self.fields["number"].required = False
        self.fields["comment"].required = False
        if "instance" in kwargs:
            instance = kwargs["instance"]
            self.instance = instance
            if hasattr(instance, "pk") and instance.pk:
                self.fields["number"].disabled = True

    class Meta:
        model = Formula
        fields = ["name", "number", "comment"]
        widgets = {"comment": forms.Textarea(attrs={"maxlength": 4000})}
        labels = {"number": "Formula#"}


class FormulaForm(forms.Form, utils.BootstrapFormControlMixin):
    ingredient = forms.CharField(
        required=True, widget=forms.TextInput(attrs={"placeholder": "Start typing..."})
    )
    quantity = forms.DecimalField(required=True, min_value=0.00001)
    unit = forms.ChoiceField(
        choices=lambda: BLANK_CHOICE_DASH + get_unit_choices(), required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_ingredient(self):
        raw = self.cleaned_data["ingredient"]
        ingr = Ingredient.objects.filter(name=raw)
        if not ingr.exists():
            raise ValidationError(
                "Ingredient with name '%(name)s' does not exist.", params={"name": raw}
            )
        return ingr[0]

    def save(self, formula, commit=True):
        instance = FormulaIngredient(
            formula=formula,
            ingredient=self.cleaned_data["ingredient"],
            quantity=self.cleaned_data["quantity"],
            unit=Unit.objects.filter(symbol=self.cleaned_data["unit"])[0],
        )
        if commit:
            instance.save()
        return instance


class FormulaFormsetBase(forms.BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        ingredients = {}
        errors = []
        for index, form in enumerate(self.forms, start=1):

            if "DELETE" not in form.cleaned_data or form.cleaned_data["DELETE"]:
                continue
            logger.info(form.cleaned_data)
            ingr_number = form.cleaned_data["ingredient"].number
            if ingr_number in ingredients:
                errors.append(
                    ValidationError(
                        "Row %(error_row)d: Ingredient '%(name)s' "
                        "is already specified in row %(orig_row)d",
                        params={
                            "name": form.cleaned_data["ingredient"].name,
                            "orig_row": ingredients[ingr_number],
                            "error_row": index,
                        },
                    )
                )
            else:
                ingredients[ingr_number] = index
        if errors:
            raise ValidationError(errors)


FormulaFormset = formset_factory(
    FormulaForm, extra=0, can_delete=True, formset=FormulaFormsetBase
)


class GoalForm(forms.Form, utils.BootstrapFormControlMixin):
    name = forms.CharField(
        max_length=100,
        strip=True,
        required=True,
        help_text="The name for this manufacturing goal",
        widget=forms.TextInput(attrs={"placeholder": "Name"}),
    )
    deadline = forms.DateField(
        required=True,
        help_text="The deadline for this goal",
        widget=forms.DateInput(attrs={"placeholder": "YYYY-MM-DD"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["deadline"].widget.attrs["class"] = (
            self.fields["deadline"].widget.attrs.get("class", "") + " datepicker-input"
        )
        self.fields["deadline"].widget.attrs["data-target"] = "#datepicker1"


class SkuQuantityForm(forms.Form, utils.BootstrapFormControlMixin):
    sku = AutocompletedCharField(
        data_source=reverse_lazy("autocomplete_skus"),
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Start typing..."}),
    )
    quantity = forms.DecimalField(required=True, min_value=0.00001)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_sku(self):
        raw = self.cleaned_data["sku"]
        sku = Sku.from_name(raw)
        if not sku:
            raise ValidationError("SKU '%(raw)s does not exist.", params={"raw": raw})
        return sku


class SkuQuantityFormsetBase(forms.BaseFormSet):
    def clean(self):
        # At this point SKUs should have been cleaned and are SKU instances.
        if any(self.errors):
            return
        skus = {}  # (sku number -> row number)
        errors = []
        index = 0
        for form in self.forms:
            if "DELETE" not in form.cleaned_data or form.cleaned_data["DELETE"]:
                # Form is either incorrect or deleted. Don't process
                continue
            index += 1
            logger.info("Processing form-%d: %s", index, form.cleaned_data)
            sku_number = form.cleaned_data["sku"].number
            if sku_number in skus:
                errors.append(
                    ValidationError(
                        "Row %(error_row)d: SKU '%(name)s' is already specified in "
                        "row %(orig_row)d",
                        params={
                            "name": form.cleaned_data["sku"].verbose_name,
                            "error_row": index,
                            "orig_row": skus[sku_number],
                        },
                    )
                )
            else:
                skus[sku_number] = index
        if not skus:
            raise ValidationError("You must specify at least one item.")
        if errors:
            raise ValidationError(errors)


SkuQuantityFormset = formset_factory(
    SkuQuantityForm, formset=SkuQuantityFormsetBase, can_delete=True, extra=1
)


class GoalFilterForm(forms.Form, utils.BootstrapFormControlMixin):
    name = forms.CharField(max_length=100, required=False)
    sort_by = forms.ChoiceField(choices=Goal.get_sortable_fields, required=True)
    users = CsvAutocompletedField(
        model=User,
        attr="username",
        data_source=reverse_lazy("autocomplete_users"),
        required=False,
        return_qs=True,
        widget=forms.TextInput(attrs={"placeholder": "Start typing..."}),
    )

    def query(self, user):
        """
        Queries the database for a set of goals.
        :param user: the user viewing the goals. This is used to check whether user is
            admin.
        :return:
        """
        query = Q()
        if self.cleaned_data["name"]:
            query &= Q(name__icontains=self.cleaned_data["name"])
        if not user.is_admin:
            query &= Q(user=user)
        else:
            if self.cleaned_data["users"]:
                query &= Q(user__in=self.cleaned_data["users"])

        results = Goal.objects.filter(query)
        if self.cleaned_data["sort_by"]:
            results = results.order_by(self.cleaned_data["sort_by"])
        return results.all()


class GoalScheduleForm(forms.ModelForm):
    """
    This form is not to be filled in by hand. It is generated by formset and completed
    by JavaScript using a timeline-scheduler
    """

    goal_item = forms.IntegerField(disabled=True)
    start_time = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M:%S.%fZ"], required=False
    )
    end_time = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M:%S.%fZ"], required=False
    )

    def clean_line(self):
        if not self.cleaned_data["line"]:
            return None
        qs = ManufacturingLine.objects.filter(shortname=self.cleaned_data["line"])
        if not qs.exists():
            raise ValidationError(
                "Manufacturing Line '%(line)s' does not exist.",
                params={"line": self.cleaned_data["line"]},
            )
        if not SkuManufacturingLine.objects.filter(
            sku=self.item.sku, line=qs[0]
        ).exists():
            raise ValidationError(
                "Manufacturing Line '%(line)s' cannot produce SKU #%(sku_number)d",
                code="invalid",
                params={
                    "line": self.cleaned_data["line"],
                    "sku_number": self.item.sku.number,
                },
            )
        logger.info("Found line %s for goal item %d", qs[0].pk, self.item.pk)
        return qs[0]

    def should_delete(self):
        return (
            "start_time" not in self.cleaned_data
            or not self.cleaned_data["start_time"]
            or "line" not in self.cleaned_data
            or not self.cleaned_data["line"]
            or "end_time" not in self.cleaned_data
            or not self.cleaned_data["end_time"]
        )

    def clean(self):
        if "line" in self.cleaned_data and self.cleaned_data["line"]:
            if (
                "start_time" not in self.cleaned_data
                or not self.cleaned_data["start_time"]
            ):
                raise ValidationError(
                    "Form tampering detected: Goal Item %(item)d has manufacturing "
                    "line but not start time.",
                    params={"item": self.item.pk},
                )
            # Regardless of what the user gives, we always compute the end time on
            # server side to prevent cheating.
            self.cleaned_data["end_time"] = utils.compute_end_time(
                self.cleaned_data["start_time"], self.item.hours
            )
        return super().clean()

    def __init__(self, *args, item, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = item
        self.fields["goal_item"].widget.attrs["data-goal-item-id"] = item.pk
        lines = item.sku.line_choices
        self.fields["line"] = forms.ChoiceField(choices=lines, required=False)

    class Meta:
        fields = ["goal_item", "line", "start_time", "end_time"]
        error_messages = {"start_time": {"invalid": "Start time is not a valid time."}}
        model = GoalSchedule


class GoalScheduleFormsetBase(forms.BaseFormSet):
    def __init__(self, *args, goal_items, **kwargs):
        self.goal_items = goal_items
        initial = kwargs.pop("initial", [])
        for item in goal_items:
            data = {"goal_item": item.pk}
            if item.scheduled:
                data["line"] = item.schedule.line.shortname
                data["start_time"] = item.schedule.start_time
            initial.append(data)
        super().__init__(*args, initial=initial, **kwargs)

        for form in self.forms:
            form.empty_permitted = True

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["item"] = self.goal_items[index]
        if hasattr(self.goal_items[index], "schedule"):
            kwargs["instance"] = self.goal_items[index].schedule
        return kwargs

    def _check_overlap(self):
        lines = defaultdict(list)
        for form in self.forms:
            if form.is_valid() and form.cleaned_data and form.cleaned_data["line"]:
                logger.info(form.cleaned_data)
                lines[form.cleaned_data["line"].shortname].append(form)

        for line, _forms in lines.items():  # "forms" is in outer scope
            if len(_forms) == 1:
                continue
            _forms.sort(key=lambda f: f.cleaned_data["start_time"])
            for i in range(len(_forms) - 1):
                end_time = utils.compute_end_time(
                    _forms[i].cleaned_data["start_time"], _forms[i].item.hours
                )
                if _forms[i + 1].cleaned_data["start_time"] < end_time:
                    raise ValidationError(
                        "Overlap detected on Manufacturing Line '%(line)s' between "
                        "item '%(item1)d' and '%(item2)d'.",
                        code="invalid",
                        params={
                            "line": line,
                            "item1": _forms[i].item.pk,
                            "item2": _forms[i + 1].item.pk,
                        },
                    )

    def clean(self):
        super().clean()
        self._check_overlap()


GoalScheduleFormset = formset_factory(
    GoalScheduleForm, formset=GoalScheduleFormsetBase, extra=0
)


class EditUserForm(forms.ModelForm, utils.BootstrapFormControlMixin):
    is_admin = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "netid", "password"]
        widgets = {"password": forms.PasswordInput()}

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        initial = kwargs.pop("initial", {})
        super().__init__(*args, instance=instance, initial=initial, **kwargs)

    def save(self, commit=False):
        instance = super().save(commit)
        users_group = Group.objects.get(name=USERS_GROUP)
        users_group.user_set.remove(instance)
        admin_group = Group.objects.get(name=ADMINS_GROUP)
        admin_group.user_set.remove(instance)
        instance.set_password(self.cleaned_data["password"])

        instance.save()

        instance.groups.add(users_group)
        if self.cleaned_data["is_admin"]:
            instance.groups.add(admin_group)
        return instance
