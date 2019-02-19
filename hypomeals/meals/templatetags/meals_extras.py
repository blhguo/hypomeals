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