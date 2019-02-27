# pylint: disable-msg=too-many-arguments
import traceback

from django.conf import settings
from meals import utils


class UserFacingException(Exception):
    """
    An abstract exception class whose subclasses may be displayed to the user. Usually
    this results in the error page being displayed, with the attached information.
    Other exceptions should not cause user-visible effects, and if one does, the generic
    Service Unavailable (500) message will be displayed.
    """
    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return self.message

    def __repr__(self):
        return f"<UserFacingException: {self.message}>"


class DuplicateException(UserFacingException):
    def __init__(
        self,
        message,
        model_name=None,
        key=None,
        value=None,
        line_num=None,
        raw_exception=None,
    ):
        """
        An exception that encapsulates all information about a duplicate instance.
        The purpose of this exception is to both signal that a duplicate has been
        detected, but also to contain enough information to construct a detailed error
        message. For example:
        "Import cannot be completed because duplicate was detected on {cls}.{key_name}.
        Earlier instance was: {existing_instance}. Raw exception: {raw_exception}."
        :param message: a message
        :param model_name: the class of the object being compared, e.g., Sku
        :param key: the attribute/key that is being compared, e.g., name
        :param value: the value of the key being repeated
        :param raw_exception: if duplicate is detected by Django's DB backend, include
            the raw DatabaseError instance as well
        """
        super().__init__(message)
        self.message = message
        self.model_name = model_name
        self.key = key
        self.value = value
        self.line_num = line_num
        self.raw_exception = raw_exception

    @utils.method_memoize_forever
    def __str__(self):
        result = self.message
        if self.model_name is not None and self.key and self.value:
            result += (
                f"\nDuplicate value '{self.value}' "
                f"detected on attribute '{self.key}' of '{self.model_name}'."
            )
        if self.line_num is not None:
            result += f"\nPrevious record at line {self.line_num}."
        if self.raw_exception and settings.DEBUG:
            result += "\nException information printed because DEBUG=True\n" + "".join(
                traceback.format_exception(
                    type(self.raw_exception),
                    self.raw_exception,
                    self.raw_exception.__traceback__,
                )
            )
        return result


class IntegrityException(UserFacingException):
    def __init__(
        self,
        message,
        line_num=None,
        referring_name=None,
        referred_name=None,
        fk_name=None,
        fk_value=None,
        raw_exception=None,
    ):
        """
        An exception that encapsulates all information about a referential integrity
        violation. Similar to DuplicateException, this is meant to contain enough
        information to formulate a detailed error message.

        For example,
        raise IntegrityException(
            f"Cannot insert SKU #{sku_number}.",
            line_num=line_num,
            referring_cls=Sku,
            referred_cls=ProductLine,
            fk_name="Product Line",
            fk_value="Soups",
            raw_exception=ex,
        )
        :param message: a message
        :param referring_name: the class that contains a reference, e.g., Sku
        :param referred_name: the class being referred to, e.g., Ingredient
        :param fk_name: the foreign key attribute being used, e.g., Ingr#
        :param fk_value: the value of the foreign key, e.g., 123
        :param raw_exception: if the violation is detected by Django's DB backend,
            include the raw IntegrityError as well.
        """
        self.message = message
        self.line_num = line_num
        self.referring_name = referring_name
        self.referred_name = referred_name
        self.fk_name = fk_name
        self.fk_value = fk_value
        self.raw_exception = raw_exception

    @utils.method_memoize_forever
    def __str__(self):
        result = self.message
        if (
            self.referring_name is not None
            and self.referred_name is not None
            and self.fk_name is not None
            and self.fk_value is not None
        ):
            result += (
                f"\nAttribute '{self.fk_name}' of '{self.referring_name}' referred to "
                f"a nonexistent value in '{self.referred_name}': '{self.fk_value}'."
            )
        if self.raw_exception is not None and settings.DEBUG:
            result += "\nException information printed because DEBUG=True\n" + "".join(
                traceback.format_exception(
                    type(self.raw_exception),
                    self.raw_exception,
                    self.raw_exception.__traceback__,
                )
            )
        return result


class CollisionException(Exception):
    def __init__(self, old_record, new_record):
        self.old_record = old_record
        self.new_record = new_record

    def __str__(self):
        return (
            f"'({self.old_record.pk}) {self.old_record}' => "
            f"'({self.new_record.pk}) {self.new_record}'"
        )


class CollisionOccurredException(Exception):
    """An intentional exception to abort a transaction"""
    pass


class AmbiguousRecordException(UserFacingException):
    def __init__(self, message, instance, matches):
        self.message = message
        self.instance = instance
        self.matches = matches
        self.model = instance.__class__

    def __str__(self):
        result = self.message
        result += (
            f"\nRecord '{self.instance}' "
            f"matched {len(self.matches)} existing record(s):"
        )
        for i, (attr, match) in enumerate(self.matches.items(), start=1):
            result += f"\n\tMatch {i}: (#{match.pk}) '{match}' on attribute '{attr}'"
        return result


class QueryException(UserFacingException):
    def __init__(self, *args, msg="A query exception has occurred", ex=None, code=None):
        """
        Initializes a new `QueryException` instance with the parameters
        :param msg: a message to include in the exception. Generally user-visible.
        :param ex: an enclosing exception, if any
        :param code: an error code, if any
        """
        self.msg = msg
        self.ex = ex
        self.code = code
        super().__init__(*args)

    def __str__(self):
        return f"{self.msg}\nUnderlying exception is {self.ex}"


class IllegalArgumentsException(UserFacingException):
    """
    Raised when the user attempts to override arguments (possibly bypassing front-end
    validation) that might result in an inconsistent state.
    """
    pass


class Skip(Exception):
    """Used in Importers to signal that a particular row should be skipped"""
    pass