import uuid
from unicodedata import normalize

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


def normalize_email(value):
    return normalize("NFKC", value or "").strip().casefold() or None


class AccountProfileQuerySet(models.QuerySet):
    def communication_recipients(self):
        return self.filter(
            updates_opt_in=True,
            consent_at__isnull=False,
            email_verified_at__isnull=False,
            email__isnull=False,
            user__is_active=True,
        )


class AccountProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField(max_length=254, unique=True, null=True, blank=True)
    updates_opt_in = models.BooleanField(default=False)
    consent_at = models.DateTimeField(null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    pending_email = models.EmailField(max_length=254, null=True, blank=True)
    email_nonce = models.UUIDField(default=uuid.uuid4, editable=False)
    email_request_nonce = models.UUIDField(default=uuid.uuid4, editable=False)

    objects = AccountProfileQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_email_case_unique"),
        ]

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        self.pending_email = normalize_email(self.pending_email)
        super().save(*args, **kwargs)
