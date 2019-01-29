from collections import OrderedDict

from django import forms
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, BLANK_CHOICE_DASH
from django.forms import formset_factory

from meals import utils
from meals.models import Sku, Ingredient, ProductLine, Upc


def get_ingredient_choices():
    return [(ing.number, ing.name) for ing in Ingredient.objects.all()]


def get_product_line_choices():
    return [(pl.name, pl.name) for pl in ProductLine.objects.all()]


class SkuFilterForm(forms.Form, utils.BootstrapFormControlMixin):

    NUM_PER_PAGE_CHOICES = (
        [(1, "1")] + [(i, str(i)) for i in range(50, 501, 50)] + [(-1, "All")]
    )

    page_num = forms.IntegerField(widget=forms.HiddenInput(), initial=1, required=False)
    num_per_page = forms.ChoiceField(choices=NUM_PER_PAGE_CHOICES, required=True)
    sort_by = forms.ChoiceField(choices=Sku.get_sortable_fields, required=True)
    keyword = forms.CharField(required=False, max_length=100)
    ingredients = forms.MultipleChoiceField(
        required=False,
        choices=get_ingredient_choices,
        # widget=forms.SelectMultiple(attrs={"style": "display: none"}),
    )
    product_lines = forms.MultipleChoiceField(
        required=False,
        choices=get_product_line_choices,
        # widget=forms.SelectMultiple(attrs={"style": "display: none"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = (
                getattr(field.widget.attrs, "class", "") + " mb-2"
            )

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
            query_filter |= Q(ingredients__in=params["ingredients"])
        if params["product_lines"]:
            query_filter |= Q(product_line__name__in=params["product_lines"])
        query = Sku.objects.filter(query_filter)
        if sort_by:
            query.order_by(sort_by)
        if num_per_page != -1:
            return Paginator(query.distinct(), num_per_page)
        return query.distinct()


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
        self.fields = reordered_fields

        if "instance" in kwargs:
            instance = kwargs["instance"]
            if hasattr(instance, "pk") and instance.pk:
                self.fields["number"].disabled = True

    def clean_case_upc(self):
        upc = self.cleaned_data["case_upc"]
        sku = Sku.objects.filter(case_upc__upc_number=upc)
        if sku.exists():
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
        return instance


class FormulaForm(forms.Form, utils.BootstrapFormControlMixin):

    ingredient = forms.CharField(
        required=True, widget=forms.TextInput(attrs={"placeholder": "Start typing..."})
    )
    quantity = forms.DecimalField(required=True)

    def __init__(self, *args, sku, **kwargs):
        super().__init__(*args, **kwargs)
        self.sku = sku

FormulaFormSet = formset_factory(FormulaForm, extra=1, can_delete=True)
