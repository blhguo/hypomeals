import re
import string

from django.core.exceptions import ValidationError

ALPHANUMERIC_CHARS = string.ascii_letters + string.digits
NETID_PATTERN = re.compile(r"[a-zA-Z]{2,3}[0-9]{0,3}")


def validate_alphanumeric(value):
    for ch in value:
        if ch not in ALPHANUMERIC_CHARS:
            raise ValidationError(
                "Character '%(ch)s' is not alphanumeric.", params={"ch": ch}
            )


def validate_netid(value):
    return bool(NETID_PATTERN.fullmatch(value))
