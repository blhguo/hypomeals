# pylint: disable-msg=too-many-arguments


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
