from django import forms


class ImportFileForm(forms.Form):
    #title = forms.CharField(max_length=50)
    Sku = forms.FileField(required=False)
    Ingredients = forms.FileField(required=False)
    Product_Lines = forms.FileField(required=False)
    Quantities = forms.FileField(required=False)


class ImportZipForm(forms.Form):
    Zip = forms.FileField(required=True)