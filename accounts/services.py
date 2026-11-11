import uuid
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import AccountProfile, normalize_email


class InvalidConfirmation(ValueError):
    pass


def email_available():
    return bool(getattr(settings, "EMAIL_ENABLED", False))


def profile_for(user):
    existing = AccountProfile.objects.filter(user=user).first()
    if existing:
        return existing
    with transaction.atomic():
        current = get_user_model().objects.select_for_update().get(pk=user.pk)
        profile, created = AccountProfile.objects.get_or_create(
            user=current, defaults={"email": normalize_email(current.email)}
        )
        if created:
            current.email = profile.email or ""
            current.save(update_fields=["email"])
            user.email = current.email
        return profile


def password_marker(user):
    return salted_hmac("accounts:email:password", user.password).hexdigest()


def send_confirmation(user, email):
    if not email_available():
        return False
    profile = profile_for(user)
    destination = normalize_email(email)
    nonce = uuid.uuid4()
    AccountProfile.objects.filter(pk=profile.pk).update(email_request_nonce=nonce)
    token = signing.dumps(
        {"user": user.pk, "nonce": str(nonce), "password": password_marker(user)},
        salt="accounts.email",
    )
    link = settings.POLISKILLED_PUBLIC_URL.rstrip("/") + reverse(
        "accounts:email_confirm", args=[token]
    )
    body = render_to_string("accounts/email_confirmation.txt", {"link": link})
    try:
        send_mail(
            "Conferma la tua email — PoliSkilled",
            body,
            settings.DEFAULT_FROM_EMAIL,
            [destination],
            fail_silently=False,
        )
    except (SMTPException, OSError):
        # Remember a first failed destination for retry, but never replace an
        # already delivered confirmation or a concurrent successful send.
        AccountProfile.objects.filter(
            pk=profile.pk,
            pending_email__isnull=True,
            email_nonce=profile.email_nonce,
            email_request_nonce=nonce,
            email=profile.email,
            email_verified_at=profile.email_verified_at,
            user__password=user.password,
        ).update(pending_email=destination)
        raise
    # An unsuccessful resend leaves the previously delivered link valid.
    # A slower old send cannot override a more recent request; no SMTP lock is held.
    updated = AccountProfile.objects.filter(
        pk=profile.pk,
        email_request_nonce=nonce,
        email=profile.email,
        email_verified_at=profile.email_verified_at,
        user__password=user.password,
    ).update(pending_email=destination, email_nonce=nonce)
    if not updated:
        raise InvalidConfirmation
    return True


def confirmation_profile(token, lock=False):
    try:
        payload = signing.loads(
            token,
            salt="accounts.email",
            max_age=getattr(settings, "EMAIL_CONFIRMATION_TIMEOUT", 86400),
        )
        queryset = AccountProfile.objects.select_related("user")
        if lock:
            queryset = queryset.select_for_update()
        profile = queryset.get(user_id=payload["user"], user__is_active=True)
        if (
            not profile.pending_email
            or not constant_time_compare(str(profile.email_nonce), payload["nonce"])
            or not constant_time_compare(password_marker(profile.user), payload["password"])
        ):
            raise InvalidConfirmation
        return profile
    except (signing.BadSignature, AccountProfile.DoesNotExist, KeyError, TypeError, ValueError):
        raise InvalidConfirmation from None


@transaction.atomic
def confirm_email(token):
    profile = confirmation_profile(token, lock=True)
    profile.email = profile.pending_email
    profile.pending_email = None
    profile.email_verified_at = timezone.now()
    profile.email_nonce = uuid.uuid4()
    profile.save(update_fields=["email", "pending_email", "email_verified_at", "email_nonce"])
    profile.user.email = profile.email
    profile.user.save(update_fields=["email"])
    return profile
