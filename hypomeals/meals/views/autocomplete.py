import functools

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from meals.models import Ingredient, ProductLine, Sku


def autocomplete(request, manager, key="name"):
    term = request.GET.get("term", "")
    items = list(
        manager.filter(**{f"{key}__istartswith": term})
        .distinct()
        .values_list(key, flat=True)
    )
    return JsonResponse(items, safe=False)


@login_required
def autocomplete_skus(request):
    # SKU names are weird...
    term = request.GET.get("term", "")
    items = [str(sku) for sku in Sku.objects.filter(name__istartswith=term).distinct()]
    return JsonResponse(items, safe=False)


autocomplete_ingredients = login_required(
    functools.partial(autocomplete, manager=Ingredient.objects)
)
autocomplete_product_lines = login_required(
    functools.partial(autocomplete, manager=ProductLine.objects)
)