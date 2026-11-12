from io import BytesIO

from django.contrib.auth.models import Group, Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from PIL import Image

from hub.models import ManagementEntry, Organization
from hub.permissions import is_reviewer

from .base import HubTestCase


class ManagementTests(HubTestCase):
    def role_url(self, person):
        return reverse("manage_role", args=[person.pk])

    def test_manager_can_grant_and_revoke_only_site_role(self):
        self.client.force_login(self.reviewer)
        response = self.client.post(
            self.role_url(self.other), {"enabled": "1", "expected": "0"}, follow=True
        )
        self.assertContains(response, "Gestore aggiunto")
        person = User.objects.get(pk=self.other.pk)
        self.assertTrue(is_reviewer(person))
        self.assertFalse(person.is_staff or person.is_superuser)
        self.client.post(self.role_url(self.other), {"enabled": "0", "expected": "1"})
        self.assertFalse(is_reviewer(User.objects.get(pk=self.other.pk)))
        self.assertEqual(ManagementEntry.objects.filter(subject=self.other).count(), 2)

    def test_person_cannot_escalate_or_see_management(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("management")).status_code, 403)
        response = self.client.post(self.role_url(self.other), {"enabled": "1", "expected": "0"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ManagementEntry.objects.exists())

    def test_group_inherited_role_does_not_offer_an_impossible_revoke(self):
        group = Group.objects.create(name="Imported reviewers")
        group.permissions.add(Permission.objects.get(codename="review_activity"))
        self.other.groups.add(group)
        self.client.force_login(self.reviewer)
        response = self.client.get(reverse("management"), {"q": self.other.username})
        self.assertNotContains(response, "Rimuovi ruolo")

    def test_role_requires_csrf_and_post_and_current_version(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.reviewer)
        self.assertEqual(
            browser.post(self.role_url(self.other), {"enabled": "1", "expected": "0"}).status_code,
            403,
        )
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(self.role_url(self.other)).status_code, 405)
        self.client.post(self.role_url(self.other), {"enabled": "1", "expected": "1"})
        self.assertFalse(is_reviewer(User.objects.get(pk=self.other.pk)))
        self.client.post(self.role_url(self.reviewer), {"enabled": "0", "expected": "1"})
        self.assertTrue(is_reviewer(User.objects.get(pk=self.reviewer.pk)))

    def test_search_finds_accounts_and_no_unowned_edit_rights(self):
        self.client.force_login(self.reviewer)
        response = self.client.get(reverse("management"), {"q": "other"})
        self.assertContains(response, "other")
        self.assertContains(response, "Rendi gestore")
        self.assertEqual(
            self.client.get(reverse("edit_proposal", args=[self.activity.pk])).status_code, 404
        )

    def test_staff_cannot_grant_privileges_using_django_admin(self):
        self.other.is_staff = True
        self.other.save()
        self.other.user_permissions.add(Permission.objects.get(codename="change_user"))
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("admin:auth_user_change", args=[self.owner.pk])).status_code,
            403,
        )


class OrganizationManagementTests(HubTestCase):
    def test_unclaimed_catalog_profiles_are_not_organization_requests(self):
        org = Organization.objects.create(
            name="Public profile", catalog_source_url="https://www.polimi.it/organization"
        )
        self.client.force_login(self.reviewer)
        response = self.client.get(reverse("management"))
        self.assertNotIn(org, response.context["organizations"])
        self.assertIn(org, response.context["all_organizations"])
        org.members.add(self.owner)
        self.assertIn(org, self.client.get(reverse("management")).context["organizations"])

    def test_duplicate_unicode_identity_is_form_error(self):
        Organization.objects.create(name="Élite")
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("edit_org", args=[self.org.pk]), self.payload_org(name="élite")
        )
        self.assertContains(response, "Un ente con questo nome esiste")

    def payload_org(self, **extra):
        return {
            "name": self.org.name,
            "website": "",
            "short_name": "V",
            "description": "",
            "revision": self.org.revision,
            **extra,
        }

    def test_only_members_can_edit_even_when_reviewer(self):
        for person in (self.other, self.reviewer):
            self.client.force_login(person)
            self.assertEqual(
                self.client.get(reverse("edit_org", args=[self.org.pk])).status_code, 403
            )

    def test_identity_change_requires_reapproval_and_stale_edit_is_rejected(self):
        self.client.force_login(self.owner)
        url = reverse("edit_org", args=[self.org.pk])
        self.client.post(url, self.payload_org(name="New identity"))
        self.org.refresh_from_db()
        self.assertFalse(self.org.verified)
        response = self.client.post(url, self.payload_org(name="Stale", revision=0))
        self.assertContains(response, "Ricarica")
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, "New identity")

    def test_catalog_source_does_not_publish_an_unreviewed_identity_change(self):
        self.org.catalog_source_url = "https://www.polimi.it/known-organization"
        self.org.save()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("edit_org", args=[self.org.pk]), self.payload_org(name="Different identity")
        )
        self.assertEqual(response.status_code, 302)
        self.org.refresh_from_db()
        self.assertFalse(self.org.verified)
        self.assertEqual(self.org.catalog_source_url, "")
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("organizations")), "Different identity")

    def test_reject_reason_resubmit_and_approve_audited(self):
        self.org.verified = False
        self.org.save()
        self.client.force_login(self.reviewer)
        url = reverse("verify_org", args=[self.org.pk])
        self.client.post(url, {"decision": "changes", "reason": " ", "revision": 0})
        self.assertFalse(ManagementEntry.objects.exists())
        self.client.post(
            url, {"decision": "changes", "reason": "Serve il sito ufficiale", "revision": 0}
        )
        self.org.refresh_from_db()
        self.assertEqual(self.org.review_reason, "Serve il sito ufficiale")
        entry = ManagementEntry.objects.get(organization=self.org)
        self.assertEqual(
            (entry.actor, entry.action, entry.reason),
            (self.reviewer, "Ente da rivedere", "Serve il sito ufficiale"),
        )
        self.client.post(url, {"decision": "approve", "revision": self.org.revision})
        self.org.refresh_from_db()
        self.assertFalse(self.org.verified)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse("my_organizations")), "Serve il sito ufficiale")
        self.client.post(
            reverse("edit_org", args=[self.org.pk]),
            self.payload_org(website="https://example.test"),
        )
        self.org.refresh_from_db()
        self.assertEqual(self.org.review_reason, "")
        self.client.force_login(self.reviewer)
        self.client.post(url, {"decision": "approve", "revision": self.org.revision})
        self.org.refresh_from_db()
        self.assertTrue(self.org.verified)
        self.assertEqual(ManagementEntry.objects.filter(organization=self.org).count(), 3)

    def test_self_verification_and_stale_decision_blocked(self):
        self.org.verified = False
        self.org.save()
        self.owner.user_permissions.add(Permission.objects.get(codename="review_activity"))
        self.client.force_login(self.owner)
        url = reverse("verify_org", args=[self.org.pk])
        self.assertEqual(self.client.post(url, {"revision": 0}).status_code, 403)
        self.client.force_login(self.reviewer)
        self.client.post(url, {"revision": 99})
        self.org.refresh_from_db()
        self.assertFalse(self.org.verified)

    def test_logo_reencoded_bounded_and_private_until_verified(self):
        self.org.verified = False
        self.org.save()
        self.client.force_login(self.owner)
        data = BytesIO()
        Image.new("RGBA", (600, 100), "red").save(data, "PNG")
        upload = SimpleUploadedFile("private-original.png", data.getvalue(), "image/png")
        self.client.post(reverse("edit_org", args=[self.org.pk]), self.payload_org(logo=upload))
        self.org.refresh_from_db()
        self.assertNotIn("private-original", self.org.logo.name)
        with self.org.logo.open() as saved:
            self.assertLessEqual(Image.open(saved).width, 512)
        url = reverse("org_logo", args=[self.org.pk])
        self.assertEqual(self.client.get(url)["Content-Type"], "image/png")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        edit_url = reverse("edit_org", args=[self.org.pk])
        self.assertEqual(self.client.get(edit_url).status_code, 403)
        self.assertTrue(self.org.logo.storage.exists(self.org.logo.name))
        self.assertEqual(self.client.post(edit_url, self.payload_org()).status_code, 403)
        self.assertTrue(self.org.logo.storage.exists(self.org.logo.name))
        self.client.force_login(self.reviewer)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.org.verified = True
        self.org.save()
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(self.org.logo.url).status_code, 404)

    def test_svg_is_not_a_logo(self):
        self.client.force_login(self.owner)
        upload = SimpleUploadedFile("evil.svg", b"<svg onload='alert(1)'/>", "image/svg+xml")
        response = self.client.post(
            reverse("edit_org", args=[self.org.pk]), self.payload_org(logo=upload)
        )
        self.assertContains(response, "immagine valida")
        self.org.refresh_from_db()
        self.assertFalse(self.org.logo)

    def test_phone_logo_orientation_is_preserved_without_metadata(self):
        self.client.force_login(self.owner)
        data = BytesIO()
        source = Image.new("RGB", (200, 100), "red")
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = "Private fixture author"
        source.save(data, "JPEG", exif=exif)
        upload = SimpleUploadedFile("phone.jpg", data.getvalue(), "image/jpeg")
        self.client.post(reverse("edit_org", args=[self.org.pk]), self.payload_org(logo=upload))
        self.org.refresh_from_db()
        with self.org.logo.open() as saved:
            image = Image.open(saved)
            self.assertEqual(image.size, (100, 200))
            self.assertEqual(dict(image.getexif()), {})
