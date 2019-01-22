from functools import wraps, update_wrapper

from django.shortcuts import redirect



def exception_to_error(func):

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            return redirect("error", e)

    return wrapper