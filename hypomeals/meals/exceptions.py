class QueryException(Exception):

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