from django.contrib.auth.models import Permission, User
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse

from hub.middleware import client_address
from hub.models import AuthThrottle, Organization, Track, TrackStep

from .base import HubTestCase


class AdminBoundaryTests(HubTestCase):
    def test_invalid_csrf_does_not_consume_auth_quota(self):
        browser = Client(enforce_csrf_checks=True)
        browser.get(reverse("login"))
        for _ in range(21):
            response = browser.post(reverse("login"), {"username": "x", "password": "y"})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(AuthThrottle.objects.count(), 0)

    def test_unicode_organization_names_have_unique_identity(self):
        Organization.objects.create(name="Élite")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Organization.objects.create(name="élite")

    def test_track_editor_cannot_see_private_activity_choices(self):
        editor = User.objects.create_user("editor", is_staff=True)
        editor.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="hub",
                codename__in=["change_track", "change_trackstep", "add_trackstep"],
            )
        )
        track = Track.objects.create(slug="admin-test", title="Test")
        step = TrackStep.objects.create(track=track, activity=self.activity)
        self.client.force_login(editor)
        response = self.client.get(reverse("admin:hub_track_change", args=[track.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.activity.title)
        self.assertEqual(response.context["inline_admin_formsets"], [])
        self.assertTrue(TrackStep.objects.filter(pk=step.pk).exists())

    def test_admin_cannot_bypass_organization_workflow(self):
        Organization.objects.create(name="Élite")
        self.owner.is_staff = self.owner.is_superuser = True
        self.owner.save()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("admin:hub_organization_add"),
            {
                "name": "élite",
                "members": [self.owner.pk],
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Organization.objects.filter(name="Élite").count(), 1)

    def test_proxy_headers_are_trusted_only_with_explicit_local_boundary(self):
        request = RequestFactory().get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_REAL_IP="203.0.113.12")
        with override_settings(TRUST_LOCAL_PROXY=False):
            self.assertEqual(client_address(request), "127.0.0.1")
        with override_settings(TRUST_LOCAL_PROXY=True):
            self.assertEqual(client_address(request), "203.0.113.12")
            request.META["REMOTE_ADDR"] = "203.0.113.30"
            self.assertEqual(client_address(request), "203.0.113.30")

    def test_track_admin_writes_also_require_reviewer_permission(self):
        editor = User.objects.create_user("track-writer", is_staff=True)
        editor.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="hub",
                codename__in=["add_track", "change_track", "delete_track"],
            )
        )
        track = Track.objects.create(slug="protected", title="Protected")
        self.client.force_login(editor)
        self.assertEqual(
            self.client.post(
                reverse("admin:hub_track_add"),
                {
                    "title": "Intrusion",
                    "slug": "intrusion",
                    "description": "No",
                },
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("admin:hub_track_change", args=[track.pk]),
                {
                    "title": "Changed",
                    "slug": track.slug,
                    "description": "No",
                },
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("admin:hub_track_delete", args=[track.pk]),
                {
                    "post": "yes",
                },
            ).status_code,
            403,
        )
        track.refresh_from_db()
        self.assertEqual(track.title, "Protected")
