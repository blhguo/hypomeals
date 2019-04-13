from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from .models import (
    User,
    Upc,
    ProductLine,
    Vendor,
    Ingredient,
    Sku,
    FormulaIngredient,
    Goal,
    GoalItem,
    Formula,
    SkuManufacturingLine,
    ManufacturingLine,
    Unit,
    GoalSchedule,
    Customer,
    Sale,
)

models = [
    Upc,
    ProductLine,
    Vendor,
    Ingredient,
    Sku,
    Formula,
    FormulaIngredient,
    Goal,
    GoalItem,
    GoalSchedule,
    ManufacturingLine,
    SkuManufacturingLine,
    Unit,
    Customer,
    Sale,
    Permission,
    ContentType
]

admin.site.register(User, UserAdmin)

for model in models:
    admin.site.register(model)
