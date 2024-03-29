"""
Django settings for HypoMeals project.

Generated by 'django-admin startproject' using Django 2.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""
import json
import os
import sys

import gspread
from google.oauth2 import service_account
from oauth2client.service_account import ServiceAccountCredentials as SAC

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "dummy"  # noqa will be replaced by credentials.json

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["web", "127.0.0.1", "localhost"]

AUTH_USER_MODEL = "meals.User"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

# Email settings
EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST", "smtp.mailgun.org")
EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("DJANGO_EMAIL_USE_TLS", "1") == "1"

CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")

# Google storage and sheets

GOOGLE_SHEETS_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
GS_BUCKET_NAME = "hypomeals"
GS_DEFAULT_ACL = "publicRead"
GOOGLE_SHEET_SPREADSHEET_NAME = "ECE458 Group 8 Task Sheet"

# Credentials

if os.path.exists(CREDENTIALS_FILE):
    with open(CREDENTIALS_FILE) as f:
        credentials = json.load(f)

        if "django" in credentials:
            SECRET_KEY = credentials["django"]["secret_key"]

        # Email configs
        if "email" in credentials:
            email_config = credentials["email"]
            EMAIL_HOST_USER = email_config["user"]
            EMAIL_HOST_PASSWORD = email_config["password"]
            EMAIL_FROM_ADDR = email_config["from"]
        else:
            EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_USER")
            EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_PASSWORD")
            EMAIL_FROM_ADDR = os.getenv("DJANGO_EMAIL_FROM")

        # Google cloud
        if "gcloud" in credentials:
            GS_CREDENTIALS = service_account.Credentials.from_service_account_info(
                credentials["gcloud"]
            )
            GOOGLE_SHEETS_OAUTH_CLIENT = SAC.from_json_keyfile_dict(
                credentials["gcloud"], scopes=GOOGLE_SHEETS_SCOPES
            )
            GOOGLE_SHEETS_CLIENT = gspread.authorize(GOOGLE_SHEETS_OAUTH_CLIENT)
        else:
            GS_CREDENTIALS = None

        # NetID
        if "netid" in credentials:
            netid_config = credentials["netid"]
            OAUTH_SECRET_KEY = netid_config["secret_key"]
            OAUTH_CLIENT_ID = netid_config["client_id"]
            OAUTH_AUTHORIZE_URL = netid_config["authorize_url"]
            OAUTH_REDIRECT_URL = "http://127.0.0.1:8000/accounts/sso"
else:
    print(
        "WARNING: Credentials file cannot be found. Django may fail to start",
        file=sys.stderr,
    )

# Database
USE_LOCAL_DB = os.getenv("DJANGO_USE_LOCAL_DB", "0") == "1"
DB_HOST = os.getenv("DJANGO_DB_HOST", "vcm-4081.vm.duke.edu")
DB_PORT = os.getenv("DJANGO_DB_PORT", "5432")

IDENTITY_API_URL = "https://api.colab.duke.edu/identity/v1/"

# Application definition

INSTALLED_APPS = [
    "meals.apps.MealsConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.humanize",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "django_celery_results",
    "django_celery_beat",
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
        "HOST": "127.0.0.1" if USE_LOCAL_DB else DB_HOST,
        "PORT": DB_PORT,
        "OPTIONS": {"sslmode": "require"},
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
        "sql_statements": {"format": "{asctime} {levelname} {message}", "style": "{"},
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
        # a file called server.log. Import logs are also sent to console.
        **{
            logger: {
                "handlers": ["console", "server_file"],
                "level": level,
                "propagate": False,
            }
            for logger, level in [
                ("django.request", "DEBUG"),
                ("django.server", "DEBUG"),
                ("django.template", "INFO"),
            ]
        },
    },
}


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "US/Eastern"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = "/static/"


# Celery
CELERY_RESULT_BACKEND = "django-db"
CELERY_REDIS_HOST = os.getenv("CELERY_REDIS_HOST", "localhost")
CELERY_REDIS_PORT = os.getenv("CELERY_REDIS_PORT", "6379")
CELERY_BROKER_URL = f"redis://{CELERY_REDIS_HOST}:{CELERY_REDIS_PORT}/0"

# Sales
SALES_INTERFACE_URL = "http://hypomeals-sales.colab.duke.edu:8080/"
SALES_REQUEST_CONNECT_TIMEOUT = 5
SALES_REQUEST_READ_TIMEOUT = 30
SALES_REQUEST_MAX_RETRIES = 5
SALES_TIMEOUT = 30
SALES_YEAR_START = 1999

# Backups
BACKUP_STORAGE_DIR = "backup/"  # will be stored on Google Cloud Storage
BACKUP_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
BACKUP_TIMEOUT = 5 * 60  # 5 minutes
BACKUP_NOTIFY_EMAIL = "moyehan@gmail.com"
BACKUP_SSH_KEY = "backup.key"
