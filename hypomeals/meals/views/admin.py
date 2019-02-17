import json
import logging
from urllib import parse as urlparse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.middleware import csrf
from django.shortcuts import render, redirect, resolve_url
from django.utils.http import is_safe_url
from django.views.decorators.debug import sensitive_post_parameters

from meals.auth import sign_in_netid_user

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
