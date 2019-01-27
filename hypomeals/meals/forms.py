from django import forms

from meals.utils import BootstrapFormControlMixin


class ImportFileForm(forms.Form, BootstrapFormControlMixin):

    sku = forms.FileField(required=False, label="SKU")
    ingredients = forms.FileField(required=False, label="Ingredients")
    product_lines = forms.FileField(required=False, label="Product Lines")
    formulas = forms.FileField(required=False, label="Formulas")


class ImportZipForm(forms.Form, BootstrapFormControlMixin):
    zip = forms.FileField(required=True, label="ZIP File")
