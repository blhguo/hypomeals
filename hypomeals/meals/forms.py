
import re
from collections import OrderedDict

from django import forms
from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, BLANK_CHOICE_DASH
from meals import bulk_import
from meals import utils
from meals.models import Sku, Ingredient, ProductLine, Upc, Vendor
from meals.utils import BootstrapFormControlMixin, FilenameRegexValidator


class ImportCsvForm(forms.Form, BootstrapFormControlMixin):

    skus = forms.FileField(
        required=False,
        label="SKU",
        validators=[
            FilenameRegexValidator(
                regex=r"skus(\S)*\.csv",
                message="Filename mismatch. Expected: "
                "skusxxx.csv where xxx is any characters.",
            )
        ],
    )
    ingredients = forms.FileField(
        required=False,
        label="Ingredients",
        validators=[
            FilenameRegexValidator(
                regex=r"ingredients(\S)*\.csv",
                message="Filename mismatch. Expected: "
                "ingredientsxxx.csv where xxx is any characters.",
            )
        ],
    )
    product_lines = forms.FileField(
        required=False,
        label="Product Lines",
        validators=[
            FilenameRegexValidator(
                regex=r"product_lines(\S)*\.csv",
                message="Filename mismatch. Expected: "
                "product_linesxxx.csv where xxx is any characters.",
            )
        ],
    )
    formula = forms.FileField(
        required=False,
        label="Formulas",
        validators=[
            FilenameRegexValidator(
                regex=r"formula(\S)*\.csv",
                message="Filename mismatch. Expected: "
                "formulaxxx.csv where xxx is any characters.",
            )
        ],
    )

    def __init__(self, *args, **kwargs):
        self._imported = False
        super().__init__(*args, **kwargs)

    def clean(self):
        if not any(self.cleaned_data.values()):
            raise ValidationError("You must upload at least one CSV file.")

        try:
            if bulk_import.process_csv_files(self.cleaned_data):
                self._imported = True
        except Exception as e:
            raise ValidationError(str(e))

        return self.cleaned_data



    @property
    def imported(self):
        return self._imported


class ImportZipForm(forms.Form, BootstrapFormControlMixin):

    zip = forms.FileField(required=False, label="ZIP File")

# pylint: disable-msg=protected-access


def get_ingredient_choices():
    return [(ing.number, ing.name) for ing in Ingredient.objects.all()]


def get_product_line_choices():
    return [(pl.name, pl.name) for pl in ProductLine.objects.all()]


def get_vendor_choices():
    return [(ven.info, ven.info) for ven in Vendor.objects.all()]


class CsvModelAttributeField(forms.CharField):
    COMMA_SPLIT_REGEX = re.compile(r",\s*")

    attr = "pk"

    def __init__(self, model, *args, attr, **kwargs):
        super().__init__(*args, **kwargs)
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
        items = {item.strip() for item in self.COMMA_SPLIT_REGEX.split(value)} - {""}
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

    page_num = forms.IntegerField(widget=forms.HiddenInput(), initial=1, required=False)
    num_per_page = forms.ChoiceField(choices=NUM_PER_PAGE_CHOICES, required=True)
    sort_by = forms.ChoiceField(choices=Ingredient.get_sortable_fields, required=True)
    keyword = forms.CharField(required=False, max_length=100)
    skus = CsvModelAttributeField(
        model=Sku,
        required=False,
        attr="name",
        widget=forms.TextInput(attrs={"placeholder": "Start typing..."}),
        help_text="Enter ingredients separated by commas"
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control mb-2"

    def query(self) -> Paginator:
        params = self.cleaned_data
        num_per_page = int(params.get("num_per_page", 50))
        sort_by = params.get("sort_by", "")
        query_filter = Q()
        if params['keyword']:
            query_filter &= Q(name__icontains=params["keyword"])
        if params["skus"]:
            query_filter |= Q(sku__name__in=params["skus"])
        query = Ingredient.objects.filter(query_filter)
        if sort_by:
            query.order_by(sort_by)
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
        help_texts = {"name": "Name of the new Ingredient."}

    def __init__(self, *args, **kwargs):
        initial = {}
        if "instance" in kwargs:
            instance = kwargs["instance"]
            if hasattr(instance, "pk") and instance.pk:
                initial.update(
                    {
                        "vendor": instance.vendor.info,
                    }
                )
        super().__init__(*args, initial=initial, **kwargs)
        reordered_fields = OrderedDict()
        for field_name in self.Meta.fields:
            if field_name in self.fields:
                reordered_fields[field_name] = self.fields[field_name]
                reordered_fields[field_name].widget.attrs["class"] = "form-control"
        self.fields = reordered_fields

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
            try:
                data["vendor"] = Vendor.objects.get(
                    info=data["vendor"]
                )
            except Vendor.DoesNotExist:
                data["vendor"] = Vendor(info=data["vendor"])
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


class SkuFilterForm(forms.Form):

    NUM_PER_PAGE_CHOICES = [(i, str(i)) for i in range(50, 501, 50)] + [(-1, "All")]

    page_num = forms.IntegerField(widget=forms.HiddenInput(), initial=1, required=False)
    num_per_page = forms.ChoiceField(choices=NUM_PER_PAGE_CHOICES, required=True)
    sort_by = forms.ChoiceField(choices=Sku.get_sortable_fields, required=True)
    keyword = forms.CharField(required=False, max_length=100)
    ingredients = CsvModelAttributeField(
        model=Ingredient,
        required=False,
        attr="name",
        widget=forms.TextInput(attrs={"placeholder": "Start typing..."}),
        help_text="Enter ingredients separated by commas"
    )
    product_lines = CsvModelAttributeField(
        model=ProductLine,
        required=False,
        attr="name",
        widget=forms.TextInput(attrs={"placeholder": "Start typing..."}),
        help_text="Enter Product Lines separated by commas"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control mb-2"

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
            query.order_by(sort_by)
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


class EditSkuForm(forms.ModelForm):

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
        ]
        exclude = ["case_upc", "unit_upc", "product_line"]
        widgets = {"comment": forms.Textarea(attrs={"maxlength": 200})}
        labels = {"number": "SKU#"}
        help_texts = {"name": "Name of the new SKU."}

    def __init__(self, *args, **kwargs):
        initial = {}
        if "instance" in kwargs:
            instance = kwargs["instance"]
            if hasattr(instance, "pk") and instance.pk:
                initial.update(
                    {
                        "case_upc": instance.case_upc.upc_number,
                        "unit_upc": instance.unit_upc.upc_number,
                        "product_line": instance.product_line.name,
                    }
                )
        super().__init__(*args, initial=initial, **kwargs)
        reordered_fields = OrderedDict()
        for field_name in self.Meta.fields:
            if field_name in self.fields:
                reordered_fields[field_name] = self.fields[field_name]
                reordered_fields[field_name].widget.attrs["class"] = "form-control"
        self.fields = reordered_fields

        if "instance" in kwargs:
            instance = kwargs["instance"]
            if hasattr(instance, "pk") and instance.pk:
                self.fields["number"].disabled = True

    @staticmethod
    def _clean_upc(upc):
        try:
            return Upc.objects.get(upc_number=upc)
        except Upc.DoesNotExist:
            return Upc(upc_number=upc)

    def clean_case_upc(self):
        return self._clean_upc(self.cleaned_data["case_upc"])

    def clean_unit_upc(self):
        return self._clean_upc(self.cleaned_data["unit_upc"])

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
        return data

    @transaction.atomic
    def save(self, commit=False):
        instance = super().save(commit)
        # Manually save the foreign keys, then attach them to the instance
        fks = ["case_upc", "unit_upc", "product_line"]
        for fk in fks:
            self.cleaned_data[fk].save()
            setattr(instance, fk, self.cleaned_data[fk])
        instance.save()
        self.save_m2m()
