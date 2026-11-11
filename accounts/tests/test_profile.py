from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.db import IntegrityError, transaction
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.forms import EmailRegistrationForm
from accounts.models import AccountProfile

from .base import NEW_PASSWORD, PASSWORD, AccountTestCase


class ProfileTests(AccountTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("accounts:profile")

    def change_email(self, email="changed@example.test", password=PASSWORD):
        self.client.force_login(self.user)
        return self.client.post(
            self.url,
            {
                "action": "email",
                "email": email,
                "current_password": password,
            },
        )

    def test_profile_requires_login_and_edits_only_the_current_account(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        other = User.objects.create_user("other")
        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            {
                "action": "profile",
                "username": "new-name",
                "user": other.pk,
                "email": "ignored@example.test",
                "is_staff": True,
            },
        )
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.user.username, "new-name")
        self.assertEqual(self.user.email, "student@example.test")
        self.assertFalse(self.user.is_staff)
        self.assertEqual(other.username, "other")

    def test_consent_is_optional_timestamped_withdrawable_and_requires_verification(self):
        self.client.force_login(self.user)
        self.assertFalse(self.profile.updates_opt_in)
        self.assertFalse(AccountProfile.objects.communication_recipients().exists())
        self.client.post(
            self.url, {"action": "profile", "username": "student", "updates_opt_in": "on"}
        )
        self.profile.refresh_from_db()
        first_consent = self.profile.consent_at
        self.assertIsNotNone(first_consent)
        self.assertFalse(AccountProfile.objects.communication_recipients().exists())
        self.profile.email_verified_at = timezone.now()
        self.profile.save()
        self.assertEqual(list(AccountProfile.objects.communication_recipients()), [self.profile])
        self.client.post(
            self.url, {"action": "profile", "username": "student", "updates_opt_in": "on"}
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.consent_at, first_consent)
        self.client.post(self.url, {"action": "profile", "username": "student"})
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.updates_opt_in)
        self.assertIsNone(self.profile.consent_at)
        self.assertFalse(AccountProfile.objects.communication_recipients().exists())

    def test_email_change_requires_password_then_confirmation_and_one_use(self):
        self.assertContains(self.change_email(password="bad"), "non è corretta")
        self.assertEqual(len(mail.outbox), 0)
        self.assertRedirects(self.change_email(email="CHANGED@EXAMPLE.TEST"), self.url)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.email, "student@example.test")
        self.assertEqual(self.profile.pending_email, "changed@example.test")
        self.assertEqual(mail.outbox[-1].to, ["changed@example.test"])
        path = self.mail_path()
        self.assertContains(self.client.get(path), "Conferma email")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "student@example.test")
        self.assertContains(self.client.post(path), "Email confermata.")
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.email, "changed@example.test")
        self.assertEqual(self.profile.email, self.user.email)
        self.assertIsNotNone(self.profile.email_verified_at)
        self.assertIsNone(self.profile.pending_email)
        self.assertContains(self.client.post(path), "è già stato usato")

    def test_expired_confirmation_resend_and_password_change_invalidate_old_links(self):
        self.change_email()
        first = self.mail_path()
        with patch(
            "django.core.signing.time.time", return_value=timezone.now().timestamp() + 86401
        ):
            self.assertContains(self.client.post(first), "è già stato usato")
        self.client.post(reverse("accounts:email_resend"))
        second = self.mail_path()
        self.assertNotEqual(first, second)
        self.assertContains(self.client.post(first), "è già stato usato")
        self.user.set_password(NEW_PASSWORD)
        self.user.save(update_fields=["password"])
        self.assertContains(self.client.post(second), "è già stato usato")

    def test_confirmation_collision_is_atomic_and_preserves_original_email(self):
        self.change_email()
        path = self.mail_path()
        other = User.objects.create_user("other", "changed@example.test")
        AccountProfile.objects.create(user=other, email=other.email)
        self.assertContains(self.client.post(path), "non è più disponibile")
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.email, "student@example.test")
        self.assertEqual(self.profile.email, "student@example.test")
        self.assertIsNone(self.profile.email_verified_at)

    def test_duplicate_username_and_email_are_rejected(self):
        other = User.objects.create_user("other", "other@example.test")
        AccountProfile.objects.create(user=other, email=other.email)
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"action": "profile", "username": "other"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertContains(self.change_email("OTHER@EXAMPLE.TEST"), "già associata")
        self.assertEqual(len(mail.outbox), 0)

    def test_database_enforces_case_insensitive_uniqueness_and_blank_demo_accounts(self):
        demo = User.objects.create_user("demo")
        AccountProfile.objects.create(user=demo, email="")
        another = User.objects.create_user("another")
        AccountProfile.objects.create(user=another, email=None)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccountProfile.objects.filter(user=demo).update(email="STUDENT@EXAMPLE.TEST")

    def test_validated_registration_race_rolls_back_new_user(self):
        def form(username):
            return EmailRegistrationForm(
                {
                    "username": username,
                    "email": "race@example.test",
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                }
            )

        first, second = form("first"), form("second")
        self.assertTrue(first.is_valid())
        self.assertTrue(second.is_valid())
        first.save()
        with self.assertRaises(IntegrityError):
            second.save()
        self.assertFalse(User.objects.filter(username="second").exists())
        self.assertEqual(AccountProfile.objects.filter(email="race@example.test").count(), 1)

    @override_settings(EMAIL_ENABLED=False)
    def test_unavailable_email_cannot_change_address(self):
        self.assertContains(self.change_email(), "Invio email non ancora disponibile")
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.pending_email)
        self.assertEqual(len(mail.outbox), 0)

    def test_provider_outage_preserves_original_and_allows_later_resend(self):
        with patch("accounts.services.send_mail", side_effect=SMTPException):
            with self.assertLogs("accounts.views", level="WARNING"):
                response = self.change_email()
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "student@example.test")
        self.client.post(reverse("accounts:email_resend"))
        self.assertEqual(mail.outbox[-1].to, ["changed@example.test"])

    def test_profile_and_confirmation_mutations_require_csrf_and_resend_is_post_only(self):
        self.change_email()
        token_path = self.mail_path()
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.user)
        for url in [
            self.url,
            reverse("accounts:email_resend"),
            token_path,
            reverse("accounts:password_change"),
        ]:
            self.assertEqual(browser.post(url, {}).status_code, 403)
        self.assertEqual(browser.get(reverse("accounts:email_resend")).status_code, 405)
        self.assertIn("no-store", self.client.get(self.url)["Cache-Control"])
        self.assertIn("no-store", self.client.get(token_path)["Cache-Control"])

    def test_email_change_attempts_are_rate_limited_even_with_wrong_password(self):
        for _ in range(5):
            self.assertEqual(self.change_email(password="wrong").status_code, 200)
        response = self.change_email(password="wrong")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "900")
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmation_and_resend_share_database_limits_across_clients(self):
        self.client.force_login(self.user)
        resend = reverse("accounts:email_resend")
        for _ in range(5):
            self.assertEqual(self.client.post(resend).status_code, 302)
        other_worker = Client()
        other_worker.force_login(self.user)
        self.assertEqual(other_worker.post(resend).status_code, 429)
        invalid = reverse("accounts:email_confirm", args=["invalid"])
        for _ in range(20):
            self.assertEqual(self.client.get(invalid).status_code, 200)
        self.assertEqual(other_worker.get(invalid).status_code, 429)
