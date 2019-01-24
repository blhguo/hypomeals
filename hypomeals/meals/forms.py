from django import forms
from .models import *

class ImportFileForm(forms.Form):
    #title = forms.CharField(max_length=50)
    Sku = forms.FileField(required=False)
    Ingredients = forms.FileField(required=False)
    Product_Lines = forms.FileField(required=False)
    Quantities = forms.FileField(required=False)

    #def clean_inputs(self):
    #check each file individually, dont reference database (only for duplicates. A map to chache results as well"ingredient number to ingredient object"
    #check for referential integrity (everything being referenced by a table exists somewhere in either the database or the map
    #follow each relationship is fulfilled
    #Doing database operations
    #^assumes all files being imported have no collisions
    #def clean_Sku(self):
