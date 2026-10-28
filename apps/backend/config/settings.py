import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for line in (
    (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []
):
    if line.strip() and not line.lstrip().startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
if len(SECRET_KEY) < 32 or SECRET_KEY.startswith("REPLACE_"):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "Set DJANGO_SECRET_KEY to a randomly generated secret of at least 32 characters."
    )
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
).split(",")
INSTALLED_APPS = ["rest_framework", "drf_spectacular", "pharmacy"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "internet_pharmacy"),
        "USER": os.getenv("MYSQL_USER", "internet_pharmacy"),
        "PASSWORD": os.environ["MYSQL_PASSWORD"],
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "PORT": os.getenv("MYSQL_PORT", "3308"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "isolation_level": "read committed",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES', time_zone='+00:00'",
        },
    }
}
DATABASE_ROUTERS = ["config.router.ExternalSchemaRouter"]
MIGRATION_MODULES = {"pharmacy": None}
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["pharmacy.api.auth.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": ["pharmacy.api.renderers.FinancialJSONRenderer"],
    "EXCEPTION_HANDLER": "pharmacy.api.errors.handle_exception",
    "DEFAULT_THROTTLE_RATES": {"login": "10/min"},
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Internet Pharmacy API",
    "VERSION": "2.0.0",
    "DESCRIPTION": "Educational pharmacy backend. Payments, shipments and prescriptions are simulated.",
    "SERVE_INCLUDE_SCHEMA": False,
}
PHARMACIST_IDS = frozenset(
    int(x) for x in os.getenv("PHARMACIST_IDS", "").split(",") if x.strip()
)
JWT_TTL_SECONDS = 900

ENABLED_PAYMENT_METHODS = frozenset(
    os.getenv(
        "ENABLED_PAYMENT_METHODS", "CARD,BANK_TRANSFER,CASH_ON_DELIVERY,ONLINE_GATEWAY"
    ).split(",")
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]
SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"] = {
    "FulfillmentMethodEnum": ["PICKUP", "COURIER", "POSTAL"],
}
