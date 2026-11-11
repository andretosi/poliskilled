import re
from smtplib import SMTPException
from unittest.mock import patch
from urllib.parse import urlsplit

from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from accounts.models import AccountProfile
from hub.tests.base import HubTestCase


@override_settings(EMAIL_ENABLED=False)
class RegistrationTests(HubTestCase):
    def signup(self, username="student", email="Student@Example.test", **extra):
        return self.client.post(
            reverse("register"),
            {
                "username": username,
                "email": email,
                "password1": "Personal-Test-Password!1234",
                "password2": "Personal-Test-Password!1234",
                **extra,
            },
        )

    def test_registration_normalizes_email_without_requiring_consent(self):
        self.assertRedirects(self.signup(), reverse("progress"))
        user = User.objects.get(username="student")
        self.assertEqual(user.email, "student@example.test")
        self.assertFalse(user.organizations.exists())
        profile = AccountProfile.objects.get(user=user)
        self.assertFalse(profile.updates_opt_in)
        self.assertIsNone(profile.consent_at)
        self.assertIsNone(profile.email_verified_at)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_consent_checkbox_starts_unchecked(self):
        response = self.client.get(reverse("register"))
        self.assertContains(response, "Tienimi nel giro: novità e attività del Poli")
        self.assertFalse(response.context["form"]["updates_opt_in"].value())
        self.assertFalse(response.context["form"].fields["updates_opt_in"].required)

    def test_explicit_consent_stores_timestamp_without_implying_verification(self):
        self.signup(updates_opt_in="on")
        profile = AccountProfile.objects.get(user__username="student")
        self.assertTrue(profile.updates_opt_in)
        self.assertIsNotNone(profile.consent_at)
        self.assertIsNone(profile.email_verified_at)
        self.assertFalse(AccountProfile.objects.communication_recipients().exists())

    def test_duplicate_normalized_registration_does_not_create_an_account(self):
        self.signup()
        self.client.logout()
        self.assertContains(
            self.signup(username="another", email="STUDENT@EXAMPLE.TEST"), "già associata"
        )
        self.assertFalse(User.objects.filter(username="another").exists())

    def test_recovery_honestly_reports_unconfigured_email(self):
        response = self.client.get("/account/password/recupera/")
        self.assertContains(response, "Invio email non ancora disponibile")
        self.assertContains(
            self.client.get(reverse("accounts:password_reset_done")),
            "Invio email non ancora disponibile",
        )

    @override_settings(
        EMAIL_ENABLED=True,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        POLISKILLED_PUBLIC_URL="https://poliskilled.example.test",
        DEFAULT_FROM_EMAIL="accounts@example.test",
    )
    def test_signup_sends_verification_but_login_is_immediate(self):
        self.assertRedirects(self.signup(updates_opt_in="on"), reverse("progress"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["student@example.test"])
        self.assertIn(
            "https://poliskilled.example.test/account/email/conferma/", mail.outbox[0].body
        )
        self.assertIn("_auth_user_id", self.client.session)
        self.assertFalse(AccountProfile.objects.communication_recipients().exists())
        link = re.search(r"https://[^\s]+", mail.outbox[0].body).group()
        self.assertContains(self.client.post(urlsplit(link).path), "Email confermata.")
        self.assertEqual(
            AccountProfile.objects.communication_recipients().get().user.username, "student"
        )

    @override_settings(EMAIL_ENABLED=True)
    def test_confirmation_outage_does_not_block_registration(self):
        with patch("accounts.views.send_confirmation", side_effect=SMTPException):
            with self.assertLogs("accounts.views", level="WARNING"):
                response = self.signup()
        self.assertRedirects(response, reverse("progress"))
        self.assertTrue(User.objects.filter(username="student").exists())
        self.assertIn("_auth_user_id", self.client.session)
