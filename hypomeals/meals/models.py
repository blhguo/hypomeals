# pylint: disable-msg=arguments-differ
import re

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.text import Truncator

from meals import utils

import logging

logger = logging.getLogger(__name__)


class User(AbstractUser):
    # This custom user class is only for future extensibility purposes
    pass


class Upc(models.Model, utils.ModelFieldsCompareMixin):
    excluded_fields = ("id",)

    upc_number = models.CharField(max_length=12, unique=True)

    def __str__(self):
        return self.upc_number

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class ProductLine(models.Model, utils.ModelFieldsCompareMixin):
    excluded_fields = ("id",)

    name = models.CharField(max_length=100, unique=True, verbose_name="Name")

    def __str__(self):
        return self.name

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class Vendor(models.Model, utils.ModelFieldsCompareMixin):
    excluded_fields = ("id",)

    info = models.CharField(max_length=200, verbose_name="Info")

    def __str__(self):
        return Truncator(self.info).words(3)

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class Ingredient(
    models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin
):
    excluded_fields = ("number",)

    name = models.CharField(
        max_length=100, verbose_name="Name", unique=True, blank=False
    )
    # TODO: Ingredient number is alphanumeric
    number = models.IntegerField(blank=False, verbose_name="Ingr#", primary_key=True)
    vendor = models.ForeignKey(Vendor, verbose_name="Vendor", on_delete=models.CASCADE)
    size = models.CharField(max_length=100, verbose_name="Size", blank=False)
    cost = models.FloatField(blank=False, verbose_name="Cost")
    comment = models.CharField(max_length=200, blank=True, verbose_name="Comment")

    def __str__(self):
        return self.name

    __repr__ = __str__

    class Meta:
        ordering = ["number"]

    @classmethod
    def get_sortable_fields(cls):
        """
        Returns a list of fields that this model is sortable by. For now this is hard-
        coded because there is no easy way to tell whether it makes sense to sort by
        a particular field.
        :return: a list of 2-tuples (field identifier, human-readable name) suitable
            for use in, for example, a ChoiceField in a form.
        """
        return [
            ("number", "Number"),
            ("name", "Name"),
            ("vendor__info", "Vendor"),
            ("size", "Size"),
            ("cost", "Cost"),
        ]

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = utils.next_alphanumeric_str(
                str(Ingredient.objects.latest("number").number)
            )
        return super().save(*args, **kwargs)


class Sku(models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin):
    excluded_fields = ("number",)
    NAME_REGEX = re.compile(r"(?P<name>.+):\s*(?P<size>.+)\s*\*\s*(?P<count>\d+)")

    name = models.CharField(max_length=32, verbose_name="Name", blank=False)

    number = models.IntegerField(
        blank=False, verbose_name="SKU#", unique=True, primary_key=True
    )
    case_upc = models.OneToOneField(
        Upc,
        blank=False,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name="Case UPC#",
    )
    unit_upc = models.ForeignKey(
        Upc,
        verbose_name="Unit UPC#",
        blank=False,
        on_delete=models.CASCADE,
        related_name="+",
    )
    unit_size = models.CharField(max_length=100, verbose_name="Unit size", blank=False)
    count = models.IntegerField(
        verbose_name="Count per case", blank=False, help_text="Number of units per case"
    )
    product_line = models.ForeignKey(
        ProductLine, verbose_name="Product Line", blank=False, on_delete=models.CASCADE
    )
    ingredients = models.ManyToManyField(
        Ingredient, verbose_name="Ingredients", through="SkuIngredient"
    )
    comment = models.CharField(max_length=200, verbose_name="Comment", blank=True)

    @classmethod
    def from_name(cls, name):
        match = cls.NAME_REGEX.search(name)
        if match:
            name = match["name"].strip()
            size = match["size"].strip()
            try:
                count = int(match["count"].strip())
            except ValueError:
                logger.exception("Cannot parse %s as integer", match["count"])
                return None
            qs = cls.objects.filter(name=name, unit_size=size, count=count)
            if qs.exists():
                return qs[0]
        return None

    def __str__(self):
        return f"{self.name}: {self.unit_size} * {self.count}"

    @property
    def proper_name(self):
        return f"{self.name}: {self.unit_size} * {self.count}"

    __repr__ = __str__

    class Meta:
        ordering = ["number"]

    @classmethod
    def get_sortable_fields(cls):
        """
        Returns a list of fields that this model is sortable by. For now this is hard-
        coded because there is no easy way to tell whether it makes sense to sort by
        a particular field.
        :return: a list of 2-tuples (field identifier, human-readable name) suitable
            for use in, for example, a ChoiceField in a form.
        """
        return [
            ("number", "Number"),
            ("name", "Name"),
            ("case_upc__upc_number", "Case UPC"),
            ("unit_upc__upc_number", "Unit UPC"),
            ("count", "Count per case"),
            ("product_line__name", "Product Line"),
        ]

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = Sku.objects.latest("number").number + 1
        return super().save(*args, **kwargs)


class SkuIngredient(
    models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin
):
    excluded_fields = ("id",)

    sku_number = models.ForeignKey(
        Sku, blank=False, on_delete=models.CASCADE, verbose_name="SKU#"
    )
    ingredient_number = models.ForeignKey(
        Ingredient, blank=False, on_delete=models.CASCADE, verbose_name="Ingr#"
    )
    quantity = models.FloatField(blank=False)

    def __str__(self):
        return f"{self.sku_number} - {self.ingredient_number} ({self.quantity})"

    __repr__ = __str__

    class Meta:
        unique_together = (("sku_number", "ingredient_number"),)


class ManufactureGoal(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="+", default=1
    )
    form_name = models.CharField(max_length=100, default="Morton")
    save_time = models.DateTimeField(default=timezone.now, blank=True)
    file = models.FileField(
        upload_to=utils.UploadToPathAndRename("pk", "manufacture_goal/"),
        default="manufacture_goal/",
    )


class ManufactureDetail(models.Model):
    form_name = models.ForeignKey(ManufactureGoal, on_delete=models.CASCADE)
    sku = models.CharField(max_length=100)
    quantity = models.IntegerField()
