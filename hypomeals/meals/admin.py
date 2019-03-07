from django.contrib import admin

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

# Register your models here.
admin.site.register(User)
admin.site.register(Upc)
admin.site.register(ProductLine)
admin.site.register(Vendor)
admin.site.register(Ingredient)
admin.site.register(Sku)
admin.site.register(FormulaIngredient)
admin.site.register(Goal)
admin.site.register(GoalItem)
admin.site.register(Formula)
admin.site.register(SkuManufacturingLine)
admin.site.register(ManufacturingLine)
admin.site.register(Unit)
admin.site.register(GoalSchedule)
admin.site.register(Customer)
admin.site.register(Sale)
