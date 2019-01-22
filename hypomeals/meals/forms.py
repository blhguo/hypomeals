import jsonpickle
from django import forms
from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Paginator

from meals.exceptions import QueryException
from meals.models import Sku, Ingredient, ProductLine


def get_ingredient_choices():
    return [(ing.number, ing.name) for ing in Ingredient.objects.all()]


def get_product_line_choices():
    return [(pl.name, pl.name) for pl in ProductLine.objects.all()]


class SkuFilterForm(forms.Form):

    NUM_PER_PAGE_CHOICES = [(i, str(i)) for i in range(50, 501, 50)] + [(-1, "All")]

    num_per_page = forms.ChoiceField(choices=NUM_PER_PAGE_CHOICES)
    sort_by = forms.ChoiceField(choices=Sku.get_sortable_fields)
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
            field.widget.attrs["class"] = "form-control mb-2"

    def query(self) -> Paginator:
        params = self.cleaned_data
        num_per_page = params.get("num_per_page", 50)
        sort_by = params.get("sort_by", "")
        query_params = {}
        if params["keyword"]:
            query_params["name__icontains"] = params["keyword"]
        if "ingredients" in params:
            query_params["ingredients__in"] = params["ingredients"]
        if "product_lines" in params:
            query_params["product_line__name__in"] = params["product_lines"]
        query = Sku.objects.filter(**query_params)
        if sort_by:
            query.order_by(sort_by)
        return Paginator(query.all(), num_per_page)
