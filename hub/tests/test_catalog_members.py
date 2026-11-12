from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import Client
from django.urls import reverse

from hub.management_service import link_organization_member
from hub.models import ManagementEntry, Organization
from hub.tests.base import HubTestCase


class CatalogMemberTests(HubTestCase):
    def setUp(self):
        self.catalog_org = Organization.objects.create(
            name="Catalog entity", catalog_source_url="https://example.test/entity"
        )
        self.url = reverse("link_org_member", args=[self.catalog_org.pk])

    def test_only_manager_can_link_and_cannot_link_themselves(self):
        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.post(self.url, {"username": "owner", "revision": "0"}).status_code, 403
        )
        self.client.force_login(self.reviewer)
        for username in ("reviewer", "missing"):
            self.client.post(self.url, {"username": username, "revision": "0"})
        self.assertFalse(self.catalog_org.members.exists())
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.reviewer)
        self.assertEqual(
            csrf.post(self.url, {"username": "owner", "revision": "0"}).status_code, 403
        )

    def test_link_is_audited_separate_from_approval_and_checks_stale_versions(self):
        self.client.force_login(self.reviewer)
        self.assertEqual(
            self.client.post(self.url, {"username": "owner", "revision": "0"}).status_code, 302
        )
        self.catalog_org.refresh_from_db()
        self.assertFalse(self.catalog_org.verified)
        self.assertEqual(self.catalog_org.members.get(), self.owner)
        entry = ManagementEntry.objects.get(organization=self.catalog_org)
        self.assertEqual(entry.subject, self.owner)
        self.client.post(self.url, {"username": "other", "revision": "0"})
        self.assertEqual(self.catalog_org.members.count(), 1)
        self.client.post(
            self.url, {"username": "owner", "revision": str(self.catalog_org.revision)}
        )
        self.assertEqual(ManagementEntry.objects.filter(organization=self.catalog_org).count(), 1)
        self.client.post(
            reverse("verify_org", args=[self.catalog_org.pk]),
            {"decision": "approve", "revision": self.catalog_org.revision},
        )
        self.catalog_org.refresh_from_db()
        self.assertTrue(self.catalog_org.verified)

    def test_inactive_targets_and_revoked_manager_authority_are_rechecked(self):
        User.objects.create_user("inactive", is_active=False)
        self.client.force_login(self.reviewer)
        self.client.post(self.url, {"username": "inactive", "revision": "0"})
        self.assertFalse(self.catalog_org.members.exists())
        self.assertTrue(self.reviewer.has_perm("hub.review_activity"))
        self.reviewer.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            link_organization_member(self.reviewer, self.catalog_org.pk, "owner", "0")
