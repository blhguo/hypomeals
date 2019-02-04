import functools
import logging
import os
import os.path
import random
import string
import time
from functools import wraps

import magic
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models.fields.related import ForeignKey
from django.shortcuts import redirect
from django.template.defaultfilters import filesizeformat
from django.utils import six as django_six
from django.utils.crypto import salted_hmac
from django.utils.deconstruct import deconstructible
from django.utils.http import int_to_base36
from six import string_types


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
def log_exceptions(func, logger=None, exclude=()):

    if logger is None:
        # If logger is not supplied, use the root logger
        logger = logging.getLogger()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if exclude:
                if any(isinstance(e, excluded) for excluded in exclude):
                    logger.debug(
                        f"{e.__class__.__name__} raised when "
                        f"calling function {func.__qualname__} but excluded."
                    )
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

    excluded_fields = ()

    @classmethod
    def compare_instances(cls, i1, i2):
        for field in cls._meta.fields:
            if field.name in cls.excluded_fields:
                continue
            value1 = getattr(i1, field.name)
            value2 = getattr(i2, field.name)
            if isinstance(field, ForeignKey):
                deep_compare_fn = getattr(
                    field.related_model, "compare_instances", None
                )
                if deep_compare_fn:
                    if not deep_compare_fn(field.related_model, value1, value2):
                        return False
            else:
                if value1 != value2:
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
    if number[0] not in {"0", "1", "6", "7", "8", "9"}:
        return False
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

    if len(s) == 0:
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
