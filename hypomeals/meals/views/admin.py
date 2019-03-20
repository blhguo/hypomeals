import json
import logging
import sys
from urllib import parse as urlparse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.middleware import csrf
from django.shortcuts import render, redirect, resolve_url, get_list_or_404
from django.urls import reverse
from django.utils.http import is_safe_url
from django.views.debug import technical_500_response, ExceptionReporter
from django.views.decorators.debug import sensitive_post_parameters

from meals import auth, utils
from meals.auth import sign_in_netid_user
from meals.exceptions import UserFacingException
from meals.forms import EditUserForm
from meals.models import User

logger = logging.getLogger(__name__)


def index(request):
    return render(request, template_name="meals/index.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("index")


def sso_start(request):
    login_redirect = request.GET.get("next", "")
    request.session["login_redirect"] = login_redirect
    params = {
        "response_type": "token",
        "redirect_uri": settings.OAUTH_REDIRECT_URL,
        "scope": "basic",
        "state": csrf.get_token(request),
        "client_id": settings.OAUTH_CLIENT_ID,
        "client_secret": settings.OAUTH_SECRET_KEY,
    }
    querystring = urlparse.urlencode(params)
    components = urlparse.urlparse(settings.OAUTH_AUTHORIZE_URL)
    url = urlparse.urlunparse(
        (components.scheme, components.netloc, components.path, "", querystring, "")
    )
    return redirect(url)


@sensitive_post_parameters("fragment")
def sso_landing(request):
    error = request.GET.get("error", None)
    if error:
        logger.error(
            "OAuth provider returned error '%s': %s",
            error,
            request.GET.get("error_description"),
        )
        messages.error(
            request,
            "You did not authorize HypoMeals to log in with NetID. "
            "Please try again below.",
        )
        return redirect("login")

    if request.is_ajax():
        fragment = request.POST.get("fragment", "#")
        params = urlparse.parse_qs(fragment[1:])
        token = params.get("access_token", [None])[0]
        if not token:
            messages.error(
                request,
                "An error occurred while logging you in: Single sign-on did not return "
                "valid access token. Please contact the administrator.",
            )
            return JsonResponse({"error": None, "resp": resolve_url("error")})

        token_type = params.get("token_type", ["Bearer"])[0]
        logger.info("User token type: %s", token_type)
        resp = requests.get(
            settings.IDENTITY_API_URL,
            headers={
                "x-api-key": settings.OAUTH_CLIENT_ID,
                "Authorization": f"{token_type} {token}",
            },
        )
        if resp.status_code != 200:
            logger.error(
                "Received error from IDENTITY_API: (%d) %s", resp.status_code, resp.text
            )
            return JsonResponse(
                {
                    "error": "Error contacting the identity API. "
                    "Please try again later.",
                    "resp": reverse("login"),
                }
            )
        if sign_in_netid_user(request, json.loads(resp.text)):
            redirect_to = request.session.get(
                "login_redirect", resolve_url(settings.LOGIN_REDIRECT_URL)
            )
            if not is_safe_url(
                redirect_to,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                redirect_to = "/"
            return JsonResponse({"error": None, "resp": redirect_to})

        messages.error(
            request,
            "An error occurred while logging you in: unable to create user. "
            "Please contact the administrator.",
        )
        return JsonResponse({"error": None, "resp": resolve_url("error")})

    return render(request, template_name="meals/accounts/oauth_landing.html")


def _find_users_by_id(user_ids):
    user_objs = User.objects.filter(pk__in=user_ids)
    found = set(user_objs.values_list("pk", flat=True))
    missing = user_ids - found
    if missing:
        raise UserFacingException(
            f"The following user IDs cannot be found: {', '.join(map(str, missing))}"
        )
    return user_objs


@login_required
@auth.user_is_admin_ajax(msg="Only an administrator may view user information.")
def users(request):
    user_objs = get_list_or_404(User)
    return render(
        request, template_name="meals/accounts/user.html", context={"users": user_objs}
    )


@login_required
@auth.user_is_admin_ajax(msg="Only an administrator may add new users.")
def add_user(request):
    if request.method == "POST":
        form = EditUserForm(request.POST)
        if form.is_valid():
            instance = form.save()
            message = f"User '{ instance.username }' added successfully"
            messages.info(request, message)
            return redirect("users")
    else:
        form = EditUserForm()
    return render(
        request, template_name="meals/accounts/edit_user.html", context={"form": form}
    )


@login_required
@auth.user_is_admin_ajax(msg="Only an administrator may edit user information.")
def edit_user(request, pk):
    instance = User.objects.filter(pk=pk)[0]
    if request.method == "POST":
        initial_data = {"is_admin": instance.is_admin, "password": instance.password}
        form = EditUserForm(request.POST, instance=instance, initial=initial_data)
        if form.is_valid():
            instance = form.save()
            messages.info(request, f"Successfully saved User '{instance.username}'")
            return redirect("users")
    else:
        initial_data = {"is_admin": instance.is_admin, "password": instance.password}
        form = EditUserForm(instance=instance, initial=initial_data)
    return render(
        request,
        template_name="meals/accounts/edit_user.html",
        context={"form": form, "edit": True, "user": instance},
    )


@login_required
@auth.user_is_admin_ajax(msg="Only an administrator may remove users.")
@utils.ajax_view
def remove_users(request):
    user_ids = set(map(int, json.loads(request.GET.get("u", "[]"))))
    if not user_ids:
        return "No user was selected."
    user_objs = _find_users_by_id(user_ids)
    superusers = user_objs.filter(is_superuser=True)
    if superusers.exists():
        raise UserFacingException(
            f"User '{superusers[0].username}' is reserved and cannot be removed."
        )
    num_deleted, _ = user_objs.delete()
    return f"Successfully deleted {num_deleted} users."


@login_required
@user_passes_test(lambda user: user.is_superuser)
def admin_settings(request):
    """
    This is a technical page that mimics the Django exception page. No exception
    is actually raised but this page prints out a bunch of useful information.

    Only visible to the superuser (not even admin).
    """

    class DummyException(Exception):
        pass

    try:
        raise DummyException(
            "This is a dummy exception only for displaying technical information."
        )
    except DummyException:
        return technical_500_response(request, *sys.exc_info())
