from django.contrib.auth.models import AbstractUser
from django.db import models


from meals import utils
from django.utils import timezone


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

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class Vendor(models.Model, utils.ModelFieldsCompareMixin):
    excluded_fields = ("id",)

    info = models.CharField(max_length=200)

    def __str__(self):
        return f"Vendor #{self.pk}"

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class Ingredient(models.Model, utils.ModelFieldsCompareMixin):
    excluded_fields = ("number",)

    name = models.CharField(max_length=100, unique=True, blank=False)
    number = models.IntegerField(blank=False, primary_key=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    size = models.CharField(max_length=100, blank=False)
    cost = models.FloatField(blank=False)
    comment = models.CharField(max_length=200, blank=True)

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
            ("name", "Name"),
            ("number", "Number"),
            ("vendor", "Vendor"),
            ("size", "Size"),
            ("cost", "Cost"),
        ]

class Sku(models.Model, utils.ModelFieldsCompareMixin):
    excluded_fields = ("number",)

    name = models.CharField(max_length=32, blank=False, unique=True)

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
    unit_size = models.CharField(max_length=100, blank=False)
    count = models.IntegerField(
        verbose_name="Count per case", blank=False, help_text="Number of units per case"
    )
    product_line = models.ForeignKey(
        ProductLine, verbose_name="Product Line", blank=False, on_delete=models.CASCADE
    )
    ingredients = models.ManyToManyField(
        Ingredient, verbose_name="Ingredients", through="SkuIngredient"
    )
    comment = models.CharField(max_length=200, blank=True)

    def __str__(self):
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
            ("name", "Name"),
            ("number", "Number"),
            ("case_upc", "Case UPC"),
            ("unit_upc", "Unit UPC"),
            ("count", "Count per case"),
            ("product_line", "Product Line"),
        ]


class SkuIngredient(models.Model, utils.ModelFieldsCompareMixin):
    excluded_fields = ("id",)

    sku_number = models.ForeignKey(Sku, blank=False, on_delete=models.CASCADE)
    ingredient_number = models.ForeignKey(
        Ingredient, blank=False, on_delete=models.CASCADE
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


class ManufactureDetail(models.Model):
    form_name = models.ForeignKey(ManufactureGoal, on_delete=models.CASCADE)
    sku = models.CharField(max_length=100)
    quantity = models.IntegerField()
