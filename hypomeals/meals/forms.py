from django import forms
from django.core.exceptions import ValidationError

from meals import bulk_import
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
