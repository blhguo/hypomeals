from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Paginator
from django.db import models
from django.contrib.auth.models import AbstractUser

import jsonpickle

from meals.exceptions import QueryException


class User(AbstractUser):
    # This custom user class is only for future extensibility purposes
    pass


class Upc(models.Model):
    upc_number = models.CharField(max_length=12, unique=True)

    def __str__(self):
        return self.upc_number

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class ProductLine(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class Vendor(models.Model):
    info = models.CharField(max_length=200)

    def __str__(self):
        return f"Vendor #{self.pk}"

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class Ingredient(models.Model):
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


class Sku(models.Model):
    name = models.CharField(max_length=32, blank=False, unique=True)
    number = models.IntegerField(
        blank=False, verbose_name="SKU Number", unique=True, primary_key=True
    )
    case_upc = models.ForeignKey(
        Upc, blank=False, on_delete=models.CASCADE, related_name="+"
    )
    unit_upc = models.ForeignKey(
        Upc, blank=False, on_delete=models.CASCADE, related_name="+"
    )
    unit_size = models.CharField(max_length=100, blank=False)
    count = models.IntegerField(blank=False)
    product_line = models.ForeignKey(ProductLine, blank=False, on_delete=models.CASCADE)
    ingredients = models.ManyToManyField(Ingredient, through="SkuIngredient")
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

    @classmethod
    def query_from_request(cls, request):
        params = request.POST
        page = int(params.get("page", "1")) - 1
        if page < 0:
            page = 0
        num_per_page = params.get("num_per_page", 50)
        sort_by = params.get("sort_by", "")
        filter_by = jsonpickle.loads(params.get("filter_by", "{}"))
        query_params = {}
        if "keyword" in filter_by:
            query_params["name__icontains"] = filter_by["keyword"]
        if "ingredients" in filter_by:
            query_params["ingredients__in"] = filter_by["ingredients"]
        if "product_lines" in filter_by:
            query_params["product_line__name__in"] = filter_by["product_lines"]
        query = Sku.objects.filter(**query_params)
        if sort_by:
            try:
                cls._meta.get_field(sort_by)
            except FieldDoesNotExist as e:
                raise QueryException(
                    msg=f"Cannot sort by {sort_by}: field does not exist.", ex=e
                )
            else:
                query.order_by(sort_by)
        return query.all()[num_per_page * page: num_per_page * (page + 1)]


class SkuIngredient(models.Model):

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
