#pylint: disable-msg=unused-wildcard-import

import os
from .settings import *  # noqa

DEBUG = False

HOSTNAME = os.getenv("HOSTNAME", "vcm-4081.vm.duke.edu")
OAUTH_REDIRECT_URL = f"https://{HOSTNAME}/accounts/sso"
STATIC_ROOT = "/srv/static/"
