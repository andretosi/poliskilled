from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth.models import User
from django.db import connection, transaction
from django.test import TestCase

from accounts.models import AccountProfile

backfill = import_module("accounts.migrations.0001_initial").backfill_accounts


class AccountMigrationTests(TestCase):
    def migrate_data(self):
        backfill(apps, SimpleNamespace(connection=connection))

    def test_backfill_preserves_accounts_and_defaults_to_unverified_without_consent(self):
        user = User.objects.create_user("legacy", "Legacy@EXAMPLE.test")
        demo = User.objects.create_user("demo")
        another_demo = User.objects.create_user("another-demo")
        self.migrate_data()
        user.refresh_from_db()
        self.assertEqual(user.email, "legacy@example.test")
        profile = AccountProfile.objects.get(user=user)
        self.assertEqual(profile.email, user.email)
        self.assertFalse(profile.updates_opt_in)
        self.assertIsNone(profile.email_verified_at)
        self.assertIsNone(profile.consent_at)
        for account in [demo, another_demo]:
            self.assertIsNone(AccountProfile.objects.get(user=account).email)
        self.assertEqual(User.objects.count(), 3)

    def test_duplicate_normalized_emails_abort_without_removing_or_mutating_users(self):
        User.objects.create_user("legacy", "Same@example.test")
        User.objects.create_user("duplicate", "same@EXAMPLE.TEST")
        original = list(User.objects.order_by("pk").values_list("pk", "email"))
        with self.assertRaisesMessage(RuntimeError, "Duplicate normalized"), transaction.atomic():
            self.migrate_data()
        self.assertEqual(list(User.objects.order_by("pk").values_list("pk", "email")), original)
        self.assertFalse(AccountProfile.objects.exists())

    def test_nfkc_equivalent_emails_are_ambiguous_and_abort(self):
        User.objects.create_user("legacy", "user@example.test")
        User.objects.create_user("duplicate", "ｕｓｅｒ@example.test")
        with self.assertRaisesMessage(RuntimeError, "Duplicate normalized"), transaction.atomic():
            self.migrate_data()
        self.assertEqual(User.objects.count(), 2)
