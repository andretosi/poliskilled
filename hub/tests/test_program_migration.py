from importlib import import_module

from django.apps import apps
from django.db import transaction

from hub.models import Organization, ReviewEntry
from hub.permissions import can_edit, can_read

from .base import HubTestCase

correct_program = import_module("hub.migrations.0004_activity_program").correct_program


class ProgramMigrationTests(HubTestCase):
    def legacy(self):
        old = Organization.objects.create(name="Passion in Action", verified=True)
        old.members.add(self.other)
        self.activity.organizations.add(old)
        ReviewEntry.objects.create(
            activity=self.activity,
            author=self.owner,
            action="Private discussion",
            revision=1,
            body="Private",
        )
        return old

    def test_merge_preserves_cohosts_and_history_without_granting_membership(self):
        old = self.legacy()
        correct_program(apps, None)
        self.activity.refresh_from_db()
        poli = Organization.objects.get(name="Politecnico di Milano")
        self.assertFalse(Organization.objects.filter(pk=old.pk).exists())
        self.assertEqual(self.activity.program, "passion")
        self.assertEqual(set(self.activity.organizations.all()), {self.org, poli})
        self.assertEqual((self.activity.status, self.activity.revision), ("pending", 1))
        self.assertEqual(self.activity.entries.get().body, "Private")
        self.assertFalse(poli.members.exists())
        self.assertFalse(can_edit(self.other, self.activity))

    def test_unverified_university_identity_aborts_without_exposing_private_work(self):
        old = self.legacy()
        poli = Organization.objects.create(name="Politecnico di Milano", verified=False)
        poli.members.add(self.reviewer)
        with self.assertRaises(RuntimeError), transaction.atomic():
            correct_program(apps, None)
        self.assertTrue(Organization.objects.filter(pk=old.pk).exists())
        self.assertFalse(self.activity.organizations.filter(pk=poli.pk).exists())
        self.assertFalse(can_edit(self.reviewer, self.activity))
        poli.members.add(self.owner)
        # An unrelated, non-reviewer account occupying the name has no access either.
        poli.members.add(self.other)
        old.members.clear()
        self.assertFalse(can_read(self.other, self.activity))
