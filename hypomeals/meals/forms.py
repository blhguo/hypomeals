# pylint: disable-msg=protected-access
import logging
import re
import zipfile
from collections import OrderedDict
from pathlib import Path

from django import forms
from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, BLANK_CHOICE_DASH
from django.forms import formset_factory
from django.urls import reverse_lazy
from django.utils import timezone

from meals import bulk_import
from meals import utils
from meals.exceptions import CollisionOccurredException
from meals.models import GoalItem, Goal
from meals.models import Sku, Ingredient, ProductLine, Upc, Vendor, Formula
from meals.models import FormulaIngredient
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


class SkuQuantityForm(forms.ModelForm):
    name = forms.CharField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs["class"] = "form-control"
        if not args:
            self.initial["name"] = ""
            self.initial["save_time"] = timezone.now()
            number = 1
        else:
            form_content = args[0]
            self.initial["name"] = form_content["name"]
            self.initial["save_time"] = timezone.now()
            number = self.get_entry_number(args[0])
        for i in range(number):
            sku_name = "sku_%s" % (i,)
            self.fields[sku_name] = forms.CharField(required=False)
            self.fields[sku_name].widget.attrs["class"] = "form-control autocomplete"
            self.fields[sku_name].widget.attrs["placeholder"] = "Sku"
            quantity_name = "quantity_%s" % (i,)
            self.fields[quantity_name] = forms.CharField(required=False)
            self.fields[quantity_name].widget.attrs["class"] = "form-control"
            self.fields[quantity_name].widget.attrs["placeholder"] = "Quantity"
            if args:
                self.initial[sku_name] = form_content[sku_name]
                self.initial[quantity_name] = form_content[quantity_name]
            else:
                self.initial[sku_name] = ""
                self.initial[quantity_name] = ""

            if i == number - 1:
                self.fields[sku_name].widget.attrs[
                    "class"
                ] = "sku-list-new form-control autocomplete"

    def clean(self):
        if self.is_valid():
            skus = set()
            quantities = set()
            sku_quantity = []
            i = 0
            sku_name = "sku_%s" % (i,)
            quantity_name = "quantity_%s" % (i,)
            while self.cleaned_data.get(sku_name) or self.cleaned_data.get(
                quantity_name
            ):
                sku = self.cleaned_data[sku_name]
                quantity = self.cleaned_data[quantity_name]
                print("DEBUG", sku, quantity)
                if Sku.from_name(sku) is None:
                    err_message = "This SKU %s is not a valid one!" % (sku,)
                    self.add_error(sku_name, err_message)

                if quantity == "":
                    err_message = "Quantity is a required field"
                    self.add_error(quantity_name, err_message)

                if sku == "":
                    err_message = "Sku is a required field"
                    self.add_error(sku_name, err_message)

                if sku in skus:
                    self.add_error(sku_name, "Duplicate")
                else:
                    skus.add(sku)
                    quantities.add(quantity)
                    sku_quantity.append((sku, quantity))
                i += 1
                sku_name = "sku_%s" % (i,)
                quantity_name = "quantity_%s" % (i,)
            self.cleaned_data["sku_quantity"] = sku_quantity

    def save_file(self, request, file):
        if self.is_valid():
            sq = self.instance
            sq.name = self.cleaned_data["name"]
            sq.user = request.user
            sq.file.save("temp", file)
            sq.save()
            for sku, quantity in self.cleaned_data["sku_quantity"]:
                GoalItem.objects.create(name=sq, sku=sku, quantity=quantity)
        else:
            print(self.errors)

    def get_interest_fields(self):
        for sku_name in self.fields:
            if sku_name.startswith("sku_"):
                sku_index = sku_name.split("_")[1]
                quantity_name = "quantity_%s" % (sku_index,)
                yield sku_index, self[sku_name], self[quantity_name]

    def get_entry_number(self, request):
        cnt = 0
        while ("sku_" + str(cnt)) in request:
            cnt += 1
        return cnt

    class Meta:
        model = Goal
        fields = ["name"]


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


class CsvAutocompletedField(AutocompletedCharField):

    attr = "pk"

    def __init__(self, model, *args, attr, data_source, **kwargs):
        super().__init__(*args, data_source=data_source, is_multiple=True, **kwargs)
        try:
            model._meta.get_field(attr)
        except FieldDoesNotExist:
            raise AssertionError(
                f"Model '{model._meta.model_name}' has no attribute '{attr}'"
            )
        self.model = model
        self.attr = attr

    def clean(self, value):
        # Get rid of any empty values
        items = {item.strip() for item in COMMA_SPLIT_REGEX.split(value)} - {""}
        if not items:
            return items
        query = Q(**{f"{self.attr}__in": items})
        found = set(self.model.objects.filter(query).values_list(self.attr, flat=True))
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
        return found


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
            query_filter &= Q(name__icontains=params["keyword"])
        if params["skus"]:
            query_filter |= Q(sku__in=params["skus"])
        query = Ingredient.objects.filter(query_filter)
        if sort_by:
            query = query.order_by(sort_by)
        if num_per_page == -1:
            num_per_page = query.count()
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

    class Meta:
        model = Ingredient
        fields = [
            "name",
            "number",
            "vendor",
            "custom_vendor",
            "size",
            "cost",
            "comment",
        ]
        exclude = ["vendor"]
        widgets = {"comment": forms.Textarea(attrs={"maxlength": 200})}
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

    def clean(self):
        # The main thing to check for here is whether the user has supplied a custom
        # Product Line, if "Custom" was chosen in the dropdown
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

        return data

    @transaction.atomic
    def save(self, commit=False):
        instance = super().save(commit)
        # Manually save the foreign keys, then attach them to the instance
        fks = ["vendor"]
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["ingredients"].widget.attrs["placeholder"] = "Start typing..."
        self.fields["product_lines"].widget.attrs["placeholder"] = "Start typing..."

    def query(self) -> Paginator:
        # Generate the correct query, execute it, and return the requested page.
        # Requirement 2.3.2.1
        # Modified according to https://piazza.com/class/jpvlvyxg51d1nc?cid=40
        params = self.cleaned_data
        num_per_page = int(params.get("num_per_page", 50))
        sort_by = params.get("sort_by", "")
        query_filter = Q()
        if params["keyword"]:
            query_filter &= Q(name__icontains=params["keyword"])
        if params["ingredients"]:
            query_filter |= Q(ingredients__name__in=params["ingredients"])
        if params["product_lines"]:
            query_filter |= Q(product_line__name__in=params["product_lines"])
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
            return value
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
        choices=lambda: BLANK_CHOICE_DASH
        + get_formula_choices(),
        required=True,
    )
    manufacturing_line = forms.ChoiceField(
        choices=lambda: BLANK_CHOICE_DASH
        + [("custom", "Custom")]
        + get_manufacturing_line_choices(),
        required=True,
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
            "manufacturing_lines"
        ]
        exclude = ["case_upc", "unit_upc", "product_line", "formula", "manufacturing_lines"]
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
                initial.update(
                    {
                        "case_upc": instance.case_upc.upc_number,
                        "unit_upc": instance.unit_upc.upc_number,
                        "product_line": instance.product_line.name,
                        "formula": instance.formula.name,
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
                data["formula"] = Formula.objects.get(
                    name=data["formula"]
                )
            except Formula.DoesNotExist:
                data["formula"] = Formula(name=data["formula"])
        return data

    @transaction.atomic
    def save(self, commit=False):
        instance = super().save(commit)
        # Manually save the foreign keys, then attach them to the instance
        fks = ["case_upc", "unit_upc", "product_line", "formula"]
        for fk in fks:
            self.cleaned_data[fk].save()
            setattr(instance, fk, self.cleaned_data[fk])
        instance.save()
        self.save_m2m()
        return instance


class FormulaForm(forms.Form, utils.BootstrapFormControlMixin):
    ingredient = forms.CharField(
        required=True, widget=forms.TextInput(attrs={"placeholder": "Start typing..."})
    )
    quantity = forms.DecimalField(required=True, min_value=0.00001)

    def __init__(self, *args, sku, **kwargs):
        super().__init__(*args, **kwargs)
        self.sku = sku

    def clean_ingredient(self):
        raw = self.cleaned_data["ingredient"]
        ingr = Ingredient.objects.filter(name=raw)
        if not ingr.exists():
            raise ValidationError(
                "Ingredient with name '%(name)s' does not exist.", params={"name": raw}
            )
        return ingr[0]

    def save(self, commit=True):
        instance = FormulaIngredient(
            sku_number=self.sku,
            ingredient_number=self.cleaned_data["ingredient"],
            quantity=self.cleaned_data["quantity"],
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
        required=True, help_text="The deadline for this goal", widget=forms.DateInput()
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
