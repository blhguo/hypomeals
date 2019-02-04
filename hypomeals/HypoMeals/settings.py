"""
Django settings for HypoMeals project.

Generated by 'django-admin startproject' using Django 2.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os

from google.oauth2 import service_account

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "v*hru*y3-fk)j!=*qi50y_da^1v^2&32d0^-91o)67u*57hse-"  # noqa

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["web", "127.0.0.1", "localhost", "*"]

AUTH_USER_MODEL = "meals.User"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

# File Storage on Google Cloud

GOOGLE_APPLICATION_CREDENTIALS = os.path.join(BASE_DIR, "hypomeals-a5a72f65b399.json")
DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
GS_BUCKET_NAME = "hypomeals"
if os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
    GS_CREDENTIALS = service_account.Credentials.from_service_account_file(
        GOOGLE_APPLICATION_CREDENTIALS
    )
else:
    # If this file is not configured, we are likely in test mode and will / should
    # never access Google cloud anyway. So just go ahead and ignore it.
    GS_CREDENTIALS = None
GS_DEFAULT_ACL = "publicRead"

# Database
USE_LOCAL_DB = os.getenv("DJANGO_USE_LOCAL_DB", "0") == "1"

# Application definition

INSTALLED_APPS = [
    "meals.apps.MealsConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "HypoMeals.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "HypoMeals.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "Hyp0Mea1sR0cks!",
        "HOST": "127.0.0.1" if USE_LOCAL_DB else "vcm-4081.vm.duke.edu",
        "PORT": "5432",
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Logging
# https://docs.djangoproject.com/en/2.1/topics/logging/
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "{asctime} {levelname} {filename}:{lineno} "
                "{module}.{funcName} {process:d} {thread:d} {message}"
            ),
            "style": "{",
        },
        "medium": {
            "format": (
                "[{asctime}] {levelname} {filename}:{lineno} {funcName}: {message}"
            ),
            "style": "{",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
        "sql_statements": {
            "format": "{asctime} {levelname} {message} ({sql} {params})",
            "style": "{",
        },
    },
    "filters": {"require_debug_true": {"()": "django.utils.log.RequireDebugTrue"}},
    "handlers": {
        "console": {
            "level": "DEBUG",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "medium",
        },
        "sql_file": {
            "level": "DEBUG",
            "filters": [],
            "class": "logging.FileHandler",
            "formatter": "sql_statements",
            "filename": os.path.join(BASE_DIR, "logs", "sql_debug.log"),
        },
        "server_file": {
            "level": "INFO",
            "filters": [],
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_DIR, "logs", "server.log"),
        },
        "file": {
            "level": "INFO",
            "filters": [],
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_DIR, "logs", "debug.log"),
        },
    },
    "loggers": {
        # Project loggers
        # This is the catch-all root logger. It simply logs everything to console
        "": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        # This is all the loggers in our project. It logs to both the console and to
        # a special file called debug.log in the logs/ directory.
        "meals": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        # Django loggers
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        # Log all the SQL statements used in the project
        "django.db.backends": {
            "handlers": ["sql_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        # This configures all loggers related to the request-response cycle to log to
        # a file called server.log
        **{
            logger: {"handlers": ["server_file"], "level": "DEBUG", "propagate": False}
            for logger in ["django.request", "django.server", "django.template"]
        },
    },
}


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = "/static/"
