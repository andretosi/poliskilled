"""Import these settings from the project settings; never log this module's values."""

import os
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import URLValidator, validate_email

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.resend.com"
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
EMAIL_HOST_USER = "resend"
EMAIL_HOST_PASSWORD = os.environ.get("RESEND_API_KEY", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "")
POLISKILLED_PUBLIC_URL = os.environ.get("POLISKILLED_PUBLIC_URL", "").rstrip("/")
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))
PASSWORD_RESET_TIMEOUT = 3600
EMAIL_CONFIRMATION_TIMEOUT = 86400
EMAIL_ENABLED = bool(EMAIL_HOST_PASSWORD and DEFAULT_FROM_EMAIL and POLISKILLED_PUBLIC_URL)

if EMAIL_ENABLED:
    origin = urlsplit(POLISKILLED_PUBLIC_URL)
    if (
        origin.scheme != "https"
        or not origin.netloc
        or origin.username
        or origin.password
        or origin.path
        or origin.query
        or origin.fragment
    ):
        raise ImproperlyConfigured("POLISKILLED_PUBLIC_URL must be a canonical HTTPS origin.")
    try:
        URLValidator(schemes=["https"])(POLISKILLED_PUBLIC_URL)
        validate_email(DEFAULT_FROM_EMAIL)
    except ValidationError as exc:
        raise ImproperlyConfigured(
            "Configure a valid canonical public URL and verified sender address."
        ) from exc
