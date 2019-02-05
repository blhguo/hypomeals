from django.contrib import admin

from .models import (
    User,
    Upc,
    ProductLine,
    Vendor,
    Ingredient,
    Sku,
    SkuIngredient,
    ManufactureGoal,
    ManufactureDetail,
)

# Register your models here.
admin.site.register(User)
admin.site.register(Upc)
admin.site.register(ProductLine)
admin.site.register(Vendor)
admin.site.register(Ingredient)
admin.site.register(Sku)
admin.site.register(SkuIngredient)
admin.site.register(ManufactureGoal)
admin.site.register(ManufactureDetail)
