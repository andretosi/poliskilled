import re
from urllib.parse import urlsplit

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings

from accounts.models import AccountProfile

PASSWORD = "Personal-Test-Password!1234"
NEW_PASSWORD = "Changed-Password!5678"


@override_settings(
    EMAIL_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="accounts@example.test",
    POLISKILLED_PUBLIC_URL="https://poliskilled.example.test",
    PASSWORD_RESET_TIMEOUT=3600,
    EMAIL_CONFIRMATION_TIMEOUT=86400,
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class AccountTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("student", "student@example.test", PASSWORD)
        self.profile = AccountProfile.objects.create(user=self.user, email=self.user.email)

    def mail_path(self):
        link = re.search(r"https://[^\s]+", mail.outbox[-1].body).group()
        return urlsplit(link).path
