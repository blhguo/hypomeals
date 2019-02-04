import functools

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from meals.models import Ingredient, ProductLine, Sku


def autocomplete(request, manager, key="name"):
    term = request.GET.get("term", "")
    items = list(
        manager.filter(name__istartswith=term).distinct().values_list(key, flat=True)
    )
    return JsonResponse(items, safe=False)


autocomplete_skus = login_required(functools.partial(autocomplete, manager=Sku.objects))
autocomplete_ingredients = login_required(
    functools.partial(autocomplete, manager=Ingredient.objects)
)
autocomplete_product_lines = login_required(
    functools.partial(autocomplete, manager=ProductLine.objects)
)
