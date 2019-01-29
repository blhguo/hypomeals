import functools
import os
import random
import string
import time

from django.conf import settings
from django.utils import six as django_six
from django.utils.crypto import salted_hmac
from django.utils.deconstruct import deconstructible
from django.utils.http import int_to_base36
from six import string_types


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
