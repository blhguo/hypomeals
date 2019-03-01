from decimal import Decimal

from django import template


register = template.Library()


@register.simple_tag
def multiply(a, b, decimal_places=2):
    """Multiplies a by b. Simple as that."""
    result = a * b
    if isinstance(result, Decimal):
        result = result.quantize(Decimal(10) ** -decimal_places)
    return result


@register.filter
def quantize(x, decimal_places=2):
    return x.quantize(Decimal(10) ** -decimal_places)


@register.filter
def any_bool(iterable):
    return any(iterable)

@register.filter
def values_list(queryset, param):
    return queryset.values_list(param, flat=True)