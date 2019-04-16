# pylint: disable-msg=protected-access,cyclic-import

import functools
import logging
import os
import os.path
import random
import string
import time
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from functools import wraps
from typing import Type, Tuple, Callable

import magic
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Max
from django.db.models.fields.related import ForeignKey
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.defaultfilters import filesizeformat
from django.utils import six as django_six, timezone
from django.utils.crypto import salted_hmac
from django.utils.deconstruct import deconstructible
from django.utils.http import int_to_base36
from six import string_types

from meals.constants import (
    WORK_HOURS_PER_DAY,
    WORK_HOURS_END,
    WORK_HOURS_START,
    SECONDS_PER_HOUR,
    USD_EXP_REGEX,
)

logger = logging.getLogger(__name__)

def exception_to_error(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            return redirect("error", e)

    return wrapper


def _make_hash_value(timestamp, *args):
    return "".join(
        [django_six.text_type(arg) for arg in args] + [django_six.text_type(timestamp)]
    )


def make_token_with_timestamp(*args: string_types) -> string_types:
    # timestamp is number of nanoseconds since epoch
    # the last 4 digits should give us enough entropy
    timestamp = int(time.time() * 1e9)
    ts_b36 = int_to_base36(timestamp)[-4:]

    # By hashing on the internal state of the user and using state
    # that is sure to change (the password salt will change as soon as
    # the password is set, at least for current Django auth, and
    # last_login will also change), we produce a hash that will be
    # invalid as soon as it is used.
    # We limit the hash to 20 chars to keep URL short

    key_salt = "HYPOMEALS_TOKEN_GENERATOR"
    secret = settings.SECRET_KEY

    hash_value = salted_hmac(
        key_salt, _make_hash_value(timestamp, *args), secret=secret
    ).hexdigest()[::2]
    return "%s-%s" % (ts_b36, hash_value)


@deconstructible
class UploadToPathAndRename:
    """
    This class is a wrapper around an `upload_to` parameter in, for example, a
    `FileField` of a model. It renames an uploaded file to a secure, time-based token
    generated from an instance's <field_name> attribute (e.g., a name).

    Example use:
    ```
    import utils

    class MyModel(models.Model):

        name = models.CharField(required=True, unique=True, blank=False)

        file = models.FileField(
            upload_to=utils.UploadToPathAndRename("name", "desired/path/"),
            default="desired/path/default",
        )

    ```

    As an example, if an instance of MyModel has name `Test`, id `12345`, and the
    actual filename is `example_file.jpg`, the final uploaded path of the file will be:
    `desired/path/12345-c16o-b6beb44a1fa35a75fe6f.jpg`.
    """

    def __init__(self, field_name, path):
        self.field_name = field_name
        self.sub_path = path

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)
        filename = (
            make_token_with_timestamp(getattr(instance, self.field_name)) + ext[1]
        )
        if instance.pk:
            filename = f"{instance.pk}-{filename}"
        return os.path.join(self.sub_path, filename)


def parameterized(decorator):
    """
    A meta-decorator to make decorators accept parameters.

    Traditionally, in Python, to make a decorator, we simple define a function that
    returns another function. However, the problem arises when the decorator itself,
    rather than the function being decorated, wishes to accept arguments.

    :param decorator: a decorator to decorate
    :return:
    """

    @functools.wraps(decorator)
    def wrapper(*args, **kwargs):
        decorated = functools.wraps(decorator)(
            functools.partial(decorator, *args, **kwargs)
        )
        if args and callable(args[0]):
            return decorated()
        return decorated

    return wrapper


@parameterized
def inject_form_control(func, exclude_names=()):
    """
    Injects the "form-control" class to all widgets in a form.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        for name, field in self.fields.items():
            if name in exclude_names:
                continue
            field.widget.attrs["class"] = (
                field.widget.attrs.get("class", "") + " form-control"
            )

    return wrapper


class BootstrapFormControlMixin:
    """
    Injects the "form-control" class to all widgets bound to a form that inherits from
    this class.
    """

    @classmethod
    def __init_subclass__(cls, **_):

        cls.__init__ = inject_form_control(getattr(cls, "__init__"))


@deconstructible
class FilenameRegexValidator(RegexValidator):
    def __call__(self, value):
        return super().__call__(value.name)


@deconstructible
class GeneralFileValidator:
    """
    A validator for uploaded files. Adapted with modification from
    https://stackoverflow.com/questions/20272579/django-validate-file-type-of-uploaded-file
    """

    error_messages = {
        "max_size": (
            "Ensure this file size is not greater than %(max_size)s."
            " Your file size is %(size)s."
        ),
        "min_size": (
            "Ensure this file size is not less than %(min_size)s. "
            "Your file size is %(size)s."
        ),
        "content_type": "Files of type %(content_type)s are not supported.",
    }

    def __init__(self, max_size=None, min_size=None, content_types=()):
        self.max_size = max_size
        self.min_size = min_size
        self.content_types = content_types

    def __call__(self, data):
        if self.max_size is not None and data.size > self.max_size:
            params = {
                "max_size": filesizeformat(self.max_size),
                "size": filesizeformat(data.size),
            }
            raise ValidationError(self.error_messages["max_size"], "max_size", params)

        if self.min_size is not None and data.size < self.min_size:
            params = {
                "min_size": filesizeformat(self.mix_size),
                "size": filesizeformat(data.size),
            }
            raise ValidationError(self.error_messages["min_size"], "min_size", params)

        if self.content_types:
            content_type = magic.from_buffer(data.read(), mime=True)
            data.seek(0)
            if content_type not in self.content_types:
                params = {"content_type": content_type}
                raise ValidationError(
                    self.error_messages["content_type"], "content_type", params
                )

    def __eq__(self, other):
        return isinstance(other, GeneralFileValidator)


@parameterized
def log_exceptions(
    func: Callable,
    logger: logging.Logger = None,
    exclude: Tuple[Type[Exception], ...] = (),
) -> Callable:
    """
    A decorator to log all exceptions in the function, and optionally replace it with
    another exception, usually to prevent internal exceptions from being visible to
    the user.
    :param func: the function to be decorated
    :param logger: a logger to log the exception
    :param exclude: an tuple of exception classes to exclude from logging
    :return: the decorated function
    """

    if logger is None:
        # If logger is not supplied, use the root logger
        logger = logging.getLogger()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if exclude and isinstance(e, exclude):
                logger.debug(
                    f"{e.__class__.__name__} raised when "
                    f"calling function {func.__qualname__} but excluded."
                )
            else:
                logger.exception(
                    f"Exception occurred when calling function {func.__qualname__}"
                )
            raise e

    return wrapper


@parameterized
def register_to_dict(func, dct, key):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    dct[key] = wrapper
    return wrapper


def method_memoize_forever(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if "__result__" not in func.__dict__:
            func.__dict__["__result__"] = func(*args, **kwargs)
        return func.__dict__["__result__"]

    return wrapper


class ModelFieldsCompareMixin:

    compare_excluded_fields = ()

    @classmethod
    def compare_instances(cls, i1, i2):
        for field in cls._meta.fields:
            if field.name in cls.compare_excluded_fields:
                continue
            value1 = getattr(i1, field.name)
            value2 = getattr(i2, field.name)
            if isinstance(field, ForeignKey):
                if hasattr(field.related_model, "compare_instances"):
                    if not field.related_model.compare_instances(value1, value2):
                        return False
            else:
                if value1 != value2:
                    logger.info("%s %s %s %s", type(value1), value1, type(value2),
                                value2)
                    return False
        return True


def upc_check_digit(number: django_six.text_type) -> int:
    """
    Computes the check digit of a UPC-A standard code.
    Adapted from
    https://en.wikipedia.org/wiki/Universal_Product_Code#Check_digit_calculation
    :param number:
    :return:
    """
    if len(number) not in [11, 12]:
        raise ValueError("The UPC must be either 11 or 12 characters long")
    current_sum = 0
    for i in [1, 3, 5, 7, 9, 11]:
        current_sum += int(number[i - 1])
    current_sum *= 3
    for i in [2, 4, 6, 8, 10]:
        current_sum += int(number[i - 1])
    check_digit = current_sum % 10
    return 0 if check_digit == 0 else (10 - check_digit)


def is_valid_upc(number: django_six.text_type) -> bool:
    """
    Checks whether a number is compliant with the UPC-A standard. Note that according
    to the standard, first digits should also be in range [0-1,6-9].

    :param number: the UPC number to check, as a string
    :return: true iff the number is a valid UPC number
    """
    if len(number) != 12:
        return False
    # if number[0] not in {"0", "1", "6", "7", "8", "9"}:
    #     return False
    check_digit = upc_check_digit(number)
    return number[11] == str(check_digit)


def generate_random_upc() -> str:
    """
    Generates a valid UPC number
    :return: a valid UPC number, as a string
    """
    random_number = random.choice(["0", "1", "6", "7", "8", "9"])
    random_number += "".join(random.choices(string.digits, k=10))
    return random_number + str(upc_check_digit(random_number))


class AttributeResolutionMixin:
    """
    Supports the dot-notation when resolving attributes for an object. This is
    especially useful in a model with ForeignKeys. For example:

    class X(models.Model):
        name = models.CharField(...)

    class Y(models.Model, AttributeResolutionMixin):
        x = models.ForeignKey(X, ...)

    >>> y = Y.objects.create(x=X.objects.create(name="test"))
    >>> y.x.name
    'test'
    >>> getattr(y, "x.name")
    'test'
    """

    def __getattribute__(self, item):
        if "." not in item:
            return super().__getattribute__(item)
        parts = item.split(".")
        obj = super().__getattribute__(parts[0])
        for part in parts[1:]:
            obj = getattr(obj, part)
        return obj


def _do_carry(code, code_range, carry):
    code += carry
    if code > code_range[-1]:
        code = code_range[0]
        return code, 1
    return code, 0


def next_alphanumeric_str(s: str) -> str:
    """
    Generates the "next" alphanumeric string from s. For example, if s were "abc", then
    "abd" would be returned. Same goes for numbers: "ab10" will become "ab11".
    :param s: a string
    :return: the next alphanumeric string
    """

    if not s:
        raise RuntimeError("Cannot create next string from empty string")
    ascii_codes = [ord(char) for char in s]
    ascii_lower = range(97, 123)
    ascii_upper = range(65, 91)
    ascii_numbers = range(48, 58)
    carry = 1
    result = []
    for i, code in enumerate(ascii_codes[::-1]):
        if carry == 0:
            result = ascii_codes[0 : len(ascii_codes) - i] + result
            break
        is_alphanumeric = False
        for code_range in [ascii_lower, ascii_upper, ascii_numbers]:
            if code in code_range:
                code, carry = _do_carry(code, code_range, carry)
                is_alphanumeric = True
                break
        if not is_alphanumeric:
            raise RuntimeError(f"character '{chr(code)}' is not alphanumeric.")
        result.insert(0, code)
    if carry != 0:
        result.insert(0, ord("1"))
    return "".join([chr(char) for char in result])


def next_id(cls, increment_func=lambda x: x + 1, default=0):
    """
    Returns the "next" ID value that can be used as a primary key. This is a convenience
    function used in various overriden save() function in models which require an ID
    value to be autogenerated unless specified by the user.

    It computes the next ID value by the following:
    1. If the database table is empty, return 0
    2. Otherwise, return the current maximum of the value in the ID column, and call
        increment_func() with this value. This will be the return value of this
        function.
    :param cls: the model class whose ID is to be generated
    :param increment_func: a callable to increment the current maximum ID. If empty, a
        "plus one" function will be used
    :param default: the default to use if the database table is empty.
    :return: the next ID number
    """
    if cls.objects.count() == 0:
        return default
    pk_field = cls._meta.pk
    return increment_func(
        cls.objects.aggregate(Max(pk_field.name))[f"{pk_field.name}__max"]
    )


class SortedDefaultDict(defaultdict):
    """
    A default dict that is also sorted by its keys. Accepts the same arguments as the
    builtin sorted function.
    """

    def __init__(self, *args, key=None, reverse=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not callable(key):
            raise RuntimeError(f"key function {key} is not callable")
        self.key = key
        self.reverse = reverse

    def items(self):
        items = super().items()
        return sorted(items, key=lambda item: self.key(item[0]), reverse=self.reverse)

    def __iter__(self):
        return iter(self.keys())

    def keys(self):
        super_keys = super().keys()
        return sorted(super_keys, key=self.key, reverse=self.reverse)


def compute_end_time(start_time: datetime, num_hours: float) -> datetime:
    """
    Computes manufacturing end time, taking into consideration work hours of
    manufacturing lines (supplied by constants.py).
    :param start_time: datetime at which production starts
    :param num_hours: total number of hours to complete production on a MfgLine
    :return: the datetime at which production is scheduled to complete
    """
    start_time = start_time.astimezone(timezone.get_current_timezone())
    num_days = int(num_hours / WORK_HOURS_PER_DAY)
    remaining_hours = num_hours % WORK_HOURS_PER_DAY
    if remaining_hours == 0:
        num_days -= 1
        remaining_hours = WORK_HOURS_PER_DAY
    if WORK_HOURS_END >= start_time.timetz() >= WORK_HOURS_START:
        first_day_end = datetime.combine(start_time.date(), WORK_HOURS_END)
        remaining_hours -= (
            first_day_end - start_time
        ).total_seconds() / SECONDS_PER_HOUR
    end_time = start_time + timedelta(days=num_days)
    if remaining_hours > 0:
        if start_time.timetz() < WORK_HOURS_START:
            # Can use same day to finish
            end_time = datetime.combine(end_time, WORK_HOURS_START)
        else:
            end_time = datetime.combine(
                (end_time + timedelta(days=1)).date(), WORK_HOURS_START
            )
        end_time += timedelta(hours=remaining_hours)
    else:
        end_time = datetime.combine(end_time.date(), WORK_HOURS_END) + timedelta(
            hours=remaining_hours
        )
    return end_time


def ajax_view(func):
    """
    A decorator that turns a view into an AJAX-only view. This does the following
    things:
    * If the user tries to access the view via the browser, he/she is redirected to
        the error page.
    * Any string returned from the function is taken as the response, while anything
        else is taken as-is.
    * If a `UserFacingException` is raised, it is automatically converted to the "error"
        field in the `JsonResponse`, and the `resp` field is set to null.

    Works especially well with various AJAX-handling functions in `common.js`.
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        from meals.exceptions import UserFacingException  # noqa

        if request.is_ajax():
            try:
                result = func(request, *args, **kwargs)
            except UserFacingException as e:
                return JsonResponse({"error": str(e), "resp": None})
            else:
                if isinstance(result, django_six.text_type):
                    return JsonResponse({"error": None, "resp": result})
                return JsonResponse(result)
        else:
            messages.error(request, "This view is not intended for browsers.")
            return redirect("error")

    return wrapper


def chunked_read(file, chunk_size=1024):
    """
    Read a large file in chunks to reduce memory pressure
    :param file: a file-like object supporting at least "read"
    :param chunk_size: the chunk size to use. Default is 1024 bytes.
    :return: any data read, up to chunk_size, otherwise None
    """
    while True:
        data = file.read(chunk_size)
        if not data:
            break
        yield data


def parse_usd(expression: str) -> float:
    match = USD_EXP_REGEX.fullmatch(expression)
    if not match:
        raise ValueError(f"'{expression}' is not a valid USD expression")
    return Decimal(match.group(1))
