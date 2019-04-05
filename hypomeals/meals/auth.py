"""
A series of functions / decorators to aid authentication and permission checking
"""
import functools

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from meals import utils
from meals.models import User


@utils.parameterized
def permission_required_ajax(
    func, perm, msg="You do not have permission to perform this action,", reason=""
):
    """
    Checks the permission of a user in a (possibly AJAX) request, and raise an
    exception / return error response as appropriate.
    :param perm: permission, or a list of permissions
    :param msg: a message when permission is denied. *Should end in a comma*.
    :param reason: if provided, will be listed in the 403 page as reasons
    """

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
        if not request.is_ajax():
            if reason:
                messages.error(request, reason)
            raise PermissionDenied(msg)
        return JsonResponse(
            {"error": "Permission Denied", "resp": msg, "alert": msg}
        )

    return wrapper


@utils.parameterized
def user_is_admin_ajax(
    func, msg, reason="You do not have permission to perform this action,"
):
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            if not request.is_ajax():
                messages.error(request, msg)
                raise PermissionDenied(reason)
            return JsonResponse(
                {"error": "Permission Denied", "resp": reason, "alert": msg}
            )
        return func(request, *args, **kwargs)

    return wrapper


def sign_in_netid_user(request, identity):
    """
    Process an identity response from Duke identity API: https://apidocs.colab.duke.edu/

    If a NetID user already exists, log the user in. Otherwise, create a new user with
    a NetID association, add to the Users group, and log the user in.
    :param request: the HTTP request from the browser after landing
    :param identity: the identity blob returned by the identity API
    :return: True if the user is logged in. False otherwise.
    """
    if "netid" not in identity:
        return False
    user, created = User.objects.get_or_create(
        netid=identity["netid"],
        defaults={
            "first_name": identity.get("nickname", identity.get("firstName", "")),
            "last_name": identity.get("lastName", ""),
            "email": identity.get("mail", ""),
            "username": f"netid_user_{identity['netid']}",
        },
    )
    if created:
        users_group = Group.objects.get(name="Users")
        user.groups.add(users_group)
    login(request, user)
    return True
