from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, override_settings
from django.urls import resolve, reverse

from accounts.models import AccountProfile
from accounts.password_forms import PasswordChangeForm, SetPasswordForm
from accounts.services import InvalidConfirmation, confirm_email, send_confirmation
from hub.models import AuthThrottle

from .base import NEW_PASSWORD, PASSWORD, AccountTestCase


class RecoveryTests(AccountTestCase):
    def test_slower_old_send_cannot_replace_newer_confirmation(self):
        real_send = mail.send_mail

        def overlapping_send(subject, body, sender, recipients, **kwargs):
            with patch("accounts.services.send_mail", side_effect=real_send):
                send_confirmation(self.user, "newer@example.test")
            return real_send(subject, body, sender, recipients, **kwargs)

        with patch("accounts.services.send_mail", side_effect=overlapping_send):
            with self.assertRaises(InvalidConfirmation):
                send_confirmation(self.user, "older@example.test")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.pending_email, "newer@example.test")

    def test_new_superuser_can_recover_before_visiting_the_profile(self):
        user = get_user_model().objects.create_superuser(
            "server-owner", "ServerOwner@straße.test", PASSWORD
        )
        self.assertFalse(AccountProfile.objects.filter(user=user).exists())
        self.request_reset("serverowner@strasse.test")
        user.refresh_from_db()
        profile = AccountProfile.objects.get(user=user)
        self.assertEqual(user.email, "serverowner@strasse.test")
        self.assertEqual(profile.email, user.email)
        self.assertEqual(mail.outbox[-1].to, [user.email])

    def test_ambiguous_legacy_accounts_are_not_silently_reconciled(self):
        for index, email in enumerate(("Admin@straße.test", "admin@strasse.test")):
            get_user_model().objects.create_user(f"legacy-{index}", email, PASSWORD)
        self.request_reset("admin@strasse.test")
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(
            AccountProfile.objects.filter(user__username__startswith="legacy-").count(), 0
        )

    def test_failed_confirmation_resend_preserves_last_delivered_link(self):
        send_confirmation(self.user, self.user.email)
        token = resolve(self.mail_path()).kwargs["token"]
        with patch("accounts.services.send_mail", side_effect=SMTPException):
            with self.assertRaises(SMTPException):
                send_confirmation(self.user, "new@example.test")
        confirm_email(token)
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.email_verified_at)

    def test_password_forms_preserve_an_email_confirmed_while_form_is_open(self):
        for index, form_type in enumerate((PasswordChangeForm, SetPasswordForm)):
            with self.subTest(form=form_type.__name__):
                self.user.refresh_from_db()
                self.user.set_password(PASSWORD)
                self.user.save(update_fields=["password"])
                form = form_type(
                    self.user,
                    {
                        "old_password": PASSWORD,
                        "new_password1": NEW_PASSWORD,
                        "new_password2": NEW_PASSWORD,
                    },
                )
                self.assertTrue(form.is_valid(), form.errors)
                new_email = f"verified-{index}@example.test"
                send_confirmation(self.user, new_email)
                confirm_email(resolve(self.mail_path()).kwargs["token"])
                form.save()
                self.user.refresh_from_db()
                self.profile.refresh_from_db()
                self.assertEqual(self.user.email, new_email)
                self.assertEqual(self.profile.email, new_email)
                self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def request_reset(self, email="student@example.test", **kwargs):
        return self.client.post(reverse("accounts:password_reset"), {"email": email}, **kwargs)

    def test_complete_reset_then_token_reuse_fails(self):
        response = self.request_reset()
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        path = self.mail_path()
        landing = self.client.get(path)
        self.assertEqual(landing.status_code, 302)
        self.assertIn("set-password", landing.url)
        response = self.client.post(
            landing.url,
            {
                "new_password1": NEW_PASSWORD,
                "new_password2": NEW_PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        self.assertIsNone(authenticate(username=self.user.username, password=PASSWORD))
        self.assertEqual(
            authenticate(username=self.user.username, password=NEW_PASSWORD), self.user
        )
        self.assertContains(self.client.get(path), "è già stato usato")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_expired_and_invalid_tokens_cannot_set_password(self):
        self.request_reset()
        path = self.mail_path()
        future = default_token_generator._now() + timedelta(seconds=3601)
        with patch.object(default_token_generator, "_now", return_value=future):
            self.assertContains(self.client.get(path), "è già stato usato")
        invalid = path.rsplit("/", 2)[0] + "/bad-token/"
        self.assertContains(
            self.client.post(
                invalid,
                {
                    "new_password1": NEW_PASSWORD,
                    "new_password2": NEW_PASSWORD,
                },
            ),
            "è già stato usato",
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_unknown_inactive_and_unusable_accounts_have_identical_response(self):
        known = self.request_reset()
        for email in ["missing@example.test", "student@example.test"]:
            self.user.is_active = False
            self.user.save(update_fields=["is_active"])
            response = self.request_reset(email)
            self.assertEqual(response.status_code, known.status_code)
            self.assertEqual(response.url, known.url)
        self.user.is_active = True
        self.user.set_unusable_password()
        self.user.save()
        self.assertEqual(self.request_reset().url, known.url)
        self.assertEqual(len(mail.outbox), 1)

    def test_host_header_cannot_change_email_link(self):
        with override_settings(ALLOWED_HOSTS=["attacker.example.test"]):
            self.request_reset(HTTP_HOST="attacker.example.test")
        self.assertIn("https://poliskilled.example.test/account/", mail.outbox[0].body)
        self.assertNotIn("attacker.example.test", mail.outbox[0].body)

    @override_settings(EMAIL_ENABLED=False)
    def test_unconfigured_provider_is_honest_and_sends_nothing(self):
        for response in [self.client.get(reverse("accounts:password_reset")), self.request_reset()]:
            self.assertContains(response, "Invio email non ancora disponibile")
            self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(len(mail.outbox), 0)

    def test_provider_outage_does_not_reveal_account(self):
        with patch("accounts.recovery.EmailMultiAlternatives.send", side_effect=SMTPException):
            with self.assertLogs("accounts.recovery", level="WARNING"):
                known = self.request_reset()
            unknown = self.request_reset("missing@example.test")
        self.assertEqual(known.url, unknown.url)
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(len(mail.outbox), 0)

    def test_csrf_and_no_store_on_every_recovery_stage(self):
        browser = Client(enforce_csrf_checks=True)
        self.assertEqual(
            browser.post(
                reverse("accounts:password_reset"),
                {
                    "email": self.user.email,
                },
            ).status_code,
            403,
        )
        self.request_reset()
        token_url = self.mail_path()
        landing = browser.get(token_url)
        self.assertEqual(
            browser.post(
                landing.url,
                {
                    "new_password1": NEW_PASSWORD,
                    "new_password2": NEW_PASSWORD,
                },
            ).status_code,
            403,
        )
        for name in ["password_reset", "password_reset_done", "password_reset_complete"]:
            response = self.client.get(reverse("accounts:" + name))
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(response["Referrer-Policy"], "same-origin")

    @patch("accounts.throttle.time.time", return_value=1800000000)
    def test_shared_database_throttle_normalizes_target_and_preserves_hub_windows(self, clock):
        for _ in range(5):
            self.assertEqual(self.request_reset("STUDENT@EXAMPLE.TEST").status_code, 302)
        other_worker = Client()
        response = other_worker.post(
            reverse("accounts:password_reset"),
            {
                "email": "student@example.test",
            },
            REMOTE_ADDR="192.0.2.23",
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "900")
        count = AuthThrottle.objects.count()
        self.client.post(reverse("login"), {"username": "nobody", "password": "wrong"})
        self.assertEqual(AuthThrottle.objects.count(), count + 1)
        self.assertEqual(set(AuthThrottle.objects.values_list("window", flat=True)), {2000000})

    def test_direct_unsynced_user_edit_cannot_redirect_recovery(self):
        self.user.email = "other@example.test"
        self.user.save(update_fields=["email"])
        self.request_reset()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(AccountProfile.objects.get(user=self.user).email, "student@example.test")

    def test_password_change_keeps_session_and_invalidates_reset_link(self):
        self.request_reset()
        link = self.mail_path()
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": NEW_PASSWORD,
                "new_password2": NEW_PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("accounts:password_change_done"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertContains(self.client.get(link), "è già stato usato")
        self.assertIsNone(authenticate(username=self.user.username, password=PASSWORD))
