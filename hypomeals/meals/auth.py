"""
A series of functions / decorators to aid authentication and permission checking
"""
import functools

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from meals import utils


@utils.parameterized
def permission_required_ajax(func, perm):

    if not perm:
        return func

    if isinstance(perm, str):
        perms = (perm,)
    else:
        perms = perm

    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.user.has_perms(perms):
            return func(request, *args, **kwargs)
        message = "You do not have permission to execute this action."
        if not request.is_ajax():
            raise PermissionDenied(message)
        return JsonResponse(
            {"error": "Permission Denied", "resp": message, "alert": message}
        )

    return wrapper
