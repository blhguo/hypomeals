import os
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

    key_salt = "EVENT_CALENDAR_TOKEN_GENERATOR"
    secret = settings.SECRET_KEY

    hash = salted_hmac(
        key_salt, _make_hash_value(timestamp, *args), secret=secret
    ).hexdigest()[::2]
    return "%s-%s" % (ts_b36, hash)


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
