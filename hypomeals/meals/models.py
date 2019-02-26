# pylint: disable-msg=arguments-differ
import logging
import re

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import Truncator

from meals import utils
from meals.constants import ADMINS_GROUP, MIX_UNIT_EXP_REGEX, UNIT_ACCEPTED_FORMS
from meals.validators import validate_alphanumeric, validate_netid

logger = logging.getLogger(__name__)


class User(AbstractUser):
    netid = models.CharField(
        verbose_name="NetID",
        null=True,
        blank=True,
        max_length=10,
        validators=[validate_netid],
        default=None,
        unique=True,
    )

    @property
    def is_admin(self):
        return self.is_superuser or self.groups.filter(name=ADMINS_GROUP).exists()


class Upc(models.Model, utils.ModelFieldsCompareMixin):
    compare_excluded_fields = ("id",)

    upc_number = models.CharField(max_length=12, unique=True)

    def __str__(self):
        return self.upc_number

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class ProductLine(models.Model, utils.ModelFieldsCompareMixin):
    compare_excluded_fields = ("id",)

    name = models.CharField(max_length=100, unique=True, verbose_name="Name")

    def __str__(self):
        return self.name

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class Vendor(models.Model, utils.ModelFieldsCompareMixin):
    compare_excluded_fields = ("id",)

    info = models.CharField(max_length=4000, verbose_name="Info")

    def __str__(self):
        return Truncator(self.info).words(3)

    __repr__ = __str__

    class Meta:
        ordering = ["pk"]


class Unit(models.Model):
    """
    This model is not user-facing: it is only used internally to represent
    unit information. Suppose an ingredient "Flour" is measured in bags of 25000 g, to
    convert that to the base unit kg (as it is in SI), one can simply do
    >>> i = Ingredient.objects.get(...)
    >>> in_kg = i.size * i.unit.scale_factor
    >>> base_unit = Unit.objects.get(unit_type=i.unit.unit_type, is_base=True)
    >>> print(f"{i.size} g is {in_kg} {base_unit.symbol}")
    25000.0 g is 25.0 kg
    """

    UNIT_TYPES = (
        ("mass", "Mass-based"),
        ("volume", "Volume-based"),
        ("count", "Count-based"),
    )
    # The symbol of the unit, e.g., kg
    symbol = models.CharField(max_length=10, blank=False)
    # A human-readable name for the unit, e.g., metric ton
    verbose_name = models.CharField(max_length=20, blank=True)
    # A scale factor w.r.t. the base unit for this class. I.e., this unit multiplied by
    # the scale factor should equal to the base unit
    scale_factor = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        validators=[
            MinValueValidator(
                limit_value=0.000001, message="Unit scale factor must be positive."
            )
        ],
    )
    # Whether this is the base unit. This implies a scale factor of 1.0.
    is_base = models.BooleanField(default=False)
    unit_type = models.CharField(
        max_length=10, choices=UNIT_TYPES, default="count", blank=False
    )

    def __repr__(self):
        return f"<Unit: {self.symbol}>"

    __str__ = __repr__

    @classmethod
    def from_exp(cls, exp):
        """
        Parses a mixed-unit expression and return the unit, as a Unit instance. If the
        user cannot be found, a RuntimeError is raised.
        :param exp: a mixed-unit expression
        :return: a pair of (number, unit) where number is the number part, converted to
            a Python float, and unit is an instance of this class corresponding to the
            unit part.
        """
        match = MIX_UNIT_EXP_REGEX.fullmatch(exp)
        if not match:
            raise RuntimeError(f"Invalid mixed-unit expression: '{exp}'")
        if not match.group(1):
            raise RuntimeError(
                f"Invalid mixed-unit expression '{exp}': missing number part"
            )
        if not match.group(2):
            raise RuntimeError(
                f"Invalid mixed-unit expression '{exp}': missing units part"
            )
        number_part = float(match.group(1))
        unit_part = (
            match.group(2)
            .strip()
            .replace(".", "")
            .replace(" ", "")
            .casefold()
            .rstrip("s")
        )
        for symbol, accepted_forms in UNIT_ACCEPTED_FORMS.items():
            if unit_part in accepted_forms:
                return number_part, cls.objects.get(symbol=symbol)

        accepted_units = cls.objects.values_list("symbol", flat=True)
        raise RuntimeError(
            f"Unrecognized unit '{unit_part}'. "
            f"Accepted units are {', '.join(accepted_units)}."
        )


class Ingredient(
    models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin
):
    compare_excluded_fields = ("number",)

    name = models.CharField(
        max_length=100, verbose_name="Name", unique=True, blank=False
    )
    number = models.CharField(
        max_length=100,
        blank=False,
        verbose_name="Ingr#",
        primary_key=True,
        validators=[validate_alphanumeric],
    )
    vendor = models.ForeignKey(Vendor, verbose_name="Vendor", on_delete=models.CASCADE)
    size = models.DecimalField(
        verbose_name="Size",
        blank=False,
        max_digits=12,
        decimal_places=6,
        validators=[
            MinValueValidator(
                limit_value=0.000001, message="Size of ingredient must be positive."
            )
        ],
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="ingredients",
        related_query_name="ingredient",
    )

    cost = models.DecimalField(
        blank=False,
        max_digits=12,
        decimal_places=2,
        verbose_name="Cost",
        validators=[
            MinValueValidator(limit_value=0.01, message="Cost must be positive.")
        ],
    )
    comment = models.CharField(max_length=4000, blank=True, verbose_name="Comment")

    def __repr__(self):
        return f"<Ingr #{self.number}: {self.name}>"

    def __str__(self):
        return self.name

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
            self.number = utils.next_id(Ingredient, utils.next_alphanumeric_str, "0")
        return super().save(*args, **kwargs)


class Sku(models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin):
    compare_excluded_fields = ("number",)

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
        verbose_name="Count per case",
        blank=False,
        help_text="Number of units per case",
        validators=[MinValueValidator(limit_value=0)],
    )
    product_line = models.ForeignKey(
        ProductLine, verbose_name="Product Line", blank=False, on_delete=models.CASCADE
    )
    formula = models.ForeignKey(
        "Formula",
        verbose_name="Formulas",
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
        related_name="skus",
        related_query_name="sku",
    )
    formula_scale = models.DecimalField(
        verbose_name="Formula Scale Factor",
        default=1.0,
        max_digits=12,
        decimal_places=6,
        validators=[
            MinValueValidator(
                limit_value=0.000001,
                message="The formula scale factor must be positive.",
            )
        ],
    )
    manufacturing_lines = models.ManyToManyField(
        "ManufacturingLine",
        verbose_name="Manufacturing Lines",
        through="SkuManufacturingLine",
    )
    manufacturing_rate = models.DecimalField(
        verbose_name="Manufacturing Rate",
        max_digits=12,
        decimal_places=6,
        default=1.0,
        blank=False,
        help_text="Manufacturing rate for this SKU in cases per hour",
        validators=[
            MinValueValidator(
                limit_value=0.000001, message="The manufacturing rate must be positive."
            )
        ],
    )
    comment = models.CharField(max_length=4000, verbose_name="Comment", blank=True)

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

    @property
    def verbose_name(self):
        return f"{self.name}: {self.unit_size} * {self.count}"

    def __repr__(self):
        return f"<SKU #{self.number}: {self.name}>"

    def __str__(self):
        return self.verbose_name

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
            self.number = utils.next_id(Sku)
        return super().save(*args, **kwargs)


class Formula(
    models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin
):

    name = models.CharField(max_length=32, verbose_name="Name")
    number = models.IntegerField(
        blank=False, verbose_name="Formula#", primary_key=True, unique=True
    )
    ingredients = models.ManyToManyField(
        Ingredient, verbose_name="Ingredients", through="FormulaIngredient"
    )
    comment = models.CharField(max_length=4000, verbose_name="Comment")

    def __repr__(self):
        return f"<Formula #{self.number}: {self.name}>"

    def __str__(self):
        return self.name

    @classmethod
    def get_sortable_fields(cls):
        return [
            ("number", "Number"),
            ("name", "Name"),
        ]

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = utils.next_id(Formula)
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ["pk"]


class FormulaIngredient(
    models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin
):
    compare_excluded_fields = ("id",)

    formula = models.ForeignKey(
        Formula, blank=False, on_delete=models.CASCADE, verbose_name="Formula#"
    )
    ingredient = models.ForeignKey(
        Ingredient,
        blank=False,
        on_delete=models.CASCADE,
        verbose_name="Ingr#",
        related_name="formulas",
        related_query_name="formula",
    )
    quantity = models.DecimalField(blank=False, max_digits=12, decimal_places=6)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="+")

    def __repr__(self):
        return (
            f"<FormulaIngr #{self.id}: {self.formula.name} <-> "
            f"{self.ingredient.name} ({self.quantity})>"
        )

    __str__ = __repr__

    class Meta:
        unique_together = (("formula", "ingredient"),)


class ManufacturingLine(
    models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin
):
    compare_excluded_fields = ("id",)

    name = models.CharField(max_length=32, verbose_name="Name", blank=False)
    shortname = models.CharField(
        max_length=5,
        verbose_name="Short Name",
        unique=True,
        blank=False,
        help_text='A short name to quickly identify a manufacturing line. E.g., "BMP1"',
    )
    comment = models.CharField(max_length=4000, verbose_name="Comment")

    def __repr__(self):
        return f"<MfgLine #{self.pk}: {self.shortname}>"

    def __str__(self):
        return self.shortname

    class Meta:
        ordering = ["shortname"]


class SkuManufacturingLine(
    models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin
):
    compare_excluded_fields = ("id",)

    sku = models.ForeignKey(
        Sku,
        on_delete=models.CASCADE,
        # This will enable related queries with "line". For example:
        # >>> Sku.objects.filter(line__rate__ge=1.0)
        related_query_name="line",
    )
    line = models.ForeignKey(
        ManufacturingLine,
        on_delete=models.CASCADE,
        # This will create related object manager in ManufacturingLine as
        # ManufacturingLine.skus. For example:
        # >>> ManufacturingLine.skus.all()
        related_name="skus",
        # This will enable related queries with "sku". For example:
        # >>> ManufacturingLine.objects.filter(sku__name__icontains="vegetable")
        related_query_name="sku",
    )

    def __repr__(self):
        return f"<SkuMfgLine #{self.id}: {self.sku.name} <-> " f"{self.line.shortname}>"

    __str__ = __repr__

    class Meta:
        unique_together = (("sku", "line"),)


class Goal(models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin):
    compare_excluded_fields = ("id",)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        default=1,
        related_name="goals",
        related_query_name="goal",
    )
    name = models.CharField(max_length=100, blank=False)
    save_time = models.DateTimeField(default=timezone.now, blank=True)
    deadline = models.DateField(verbose_name="Deadline", blank=False)
    is_enabled = models.BooleanField(verbose_name="Enabled", blank=False, default=False)

    def __repr__(self):
        return f"<Goal #{self.id}: {self.name}>"

    def __str__(self):
        return self.name

    @property
    def completion_time(self):
        return max(
            item.completion_time
            for item in self.details.all()
            if item.completion_time is not None
        )

    @property
    def scheduled(self):
        """A goal is scheduled if all of its items have been scheduled."""
        return all(hasattr(item, "schedule") for item in self.details.all())

    @classmethod
    def get_sortable_fields(cls):
        return [
            ("-save_time", "Last Modified Time"),
            ("name", "Name"),
            ("user__first_name", "Creator Name"),
            ("deadline", "Deadline"),
        ]

    class Meta:
        unique_together = (("user", "name", "save_time"),)
        ordering = ["-save_time"]


class GoalItem(
    models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin
):
    compare_excluded_fields = ("id",)

    goal = models.ForeignKey(
        Goal,
        verbose_name="Goal",
        on_delete=models.CASCADE,
        related_name="details",
        related_query_name="detail",
    )
    sku = models.ForeignKey(
        Sku, verbose_name="SKU", on_delete=models.CASCADE, related_name="+"
    )
    quantity = models.DecimalField(
        verbose_name="Quantity",
        max_digits=12,
        decimal_places=6,
        validators=[
            MinValueValidator(limit_value=0.000001, message="Quantity must be positive")
        ],
    )

    def __repr__(self):
        return (
            f"<GoalItem #{self.id}: {self.goal.name} <-> "
            f"{self.sku.name} ({self.quantity})"
        )

    @property
    def completion_time(self):
        return self.schedule.completion_time if hasattr(self, "schedule") else None

    __str__ = __repr__

    class Meta:
        unique_together = (("goal", "sku"),)


class GoalSchedule(
    models.Model, utils.ModelFieldsCompareMixin, utils.AttributeResolutionMixin
):
    compare_excluded_fields = ("id",)

    goal_item = models.OneToOneField(
        GoalItem, on_delete=models.CASCADE, related_name="schedule", blank=False
    )
    line = models.ForeignKey(
        ManufacturingLine,
        choices=None,
        # So that we can query scheduled goal items on a particular manufacturing line
        related_name="scheduled",
        blank=False,
        on_delete=models.CASCADE,
    )
    start_time = models.DateTimeField(verbose_name="Start time", blank=False)
    end_time = models.DateTimeField(verbose_name="End time", blank=True, null=True)

    def clean(self):
        if self.line.pk not in self.goal_item.sku.skumanufacturingline_set.values_list(
            "line", flat=True
        ):
            raise ValidationError(
                "SKU '%(sku_name)s' cannot be manufactured on Line '%(line_name)s'",
                params={
                    "sku_name": self.goal_item.sku.verbose_name,
                    "line_name": self.line.shortname,
                },
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __repr__(self):
        return (
            f"<Schedule #{self.pk}: ({self.goal_item.goal.name}, "
            f"{self.goal_item.sku.name}) @ "
            f"{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}>"
        )

    @property
    def hours(self):
        """Returns the number of hours to complete a scheduled goal item."""
        return float(self.goal_item.quantity / self.goal_item.sku.manufacturing_rate)

    @property
    def completion_time(self):
        return self.end_time or utils.compute_end_time(self.start_time, self.hours)

    class Meta:
        unique_together = (("goal_item", "line"),)

    def __str__(self):
        return f"{self.goal_item.goal.name} @ {self.start_time.strftime('%Y-%m-%d')}"
