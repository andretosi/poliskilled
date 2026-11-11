from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from PIL import Image

from hub.models import Activity, Organization

from .base import HubTestCase


class SecurityTests(HubTestCase):
    def test_anonymous_cannot_read_pending(self):
        self.assertEqual(self.client.get(self.activity.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get("/"), "Test robotics")

    def test_unrelated_user_cannot_read_or_edit(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.activity.get_absolute_url()).status_code, 404)
        response = self.client.post(
            reverse("edit_proposal", args=[self.activity.pk]), self.payload(title="Hacked")
        )
        self.assertEqual(response.status_code, 404)

    def test_nonreviewer_cannot_use_queue_or_decisions(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("review_queue")).status_code, 403)
        self.assertEqual(
            self.client.post(
                reverse("decide", args=[self.activity.pk]), {"decision": "approve", "revision": 1}
            ).status_code,
            403,
        )

    def test_get_cannot_mutate(self):
        self.client.force_login(self.reviewer)
        for name in ["decide", "comment"]:
            self.assertEqual(
                self.client.get(reverse(name, args=[self.activity.pk])).status_code, 405
            )

    def test_csrf_enforced(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.owner)
        self.assertEqual(browser.post(reverse("propose"), self.payload()).status_code, 403)
        self.assertEqual(browser.post(reverse("demo_login", args=["ente"])).status_code, 403)

    def test_unverified_account_cannot_submit(self):
        self.org.verified = False
        self.org.save()
        self.client.force_login(self.owner)
        response = self.client.post(reverse("propose"), self.payload())
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(Activity.objects.count(), 1)

    def test_xss_escaped_and_security_headers(self):
        Activity.objects.filter(pk=self.activity.pk).update(
            status="published", description="<script>alert('xss')</script>"
        )
        response = self.client.get(self.activity.get_absolute_url())
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert")
        self.assertIn("default-src 'self'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")

    def test_javascript_source_url_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("propose"), self.payload(source_url="javascript:alert(1)", revision=0)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Activity.objects.count(), 1)

    def test_svg_upload_rejected(self):
        self.client.force_login(self.owner)
        upload = SimpleUploadedFile("evil.svg", b"<svg onload='alert(1)'/>", "image/svg+xml")
        self.client.post(reverse("propose"), self.payload(image=upload, revision=0))
        self.assertEqual(Activity.objects.count(), 1)

    def test_valid_image_reencoded_and_private(self):
        self.client.force_login(self.owner)
        data = BytesIO()
        Image.new("RGB", (80, 80), "green").save(data, format="PNG")
        upload = SimpleUploadedFile("original.png", data.getvalue(), "image/png")
        response = self.client.post(reverse("propose"), self.payload(image=upload, revision=0))
        self.assertEqual(response.status_code, 302)
        activity = Activity.objects.exclude(pk=self.activity.pk).get()
        self.assertTrue(activity.image.name.endswith(".jpg"))
        self.assertNotIn("original", activity.image.name)
        cover = self.client.get(reverse("cover", args=[activity.pk]))
        self.assertEqual(cover["Content-Type"], "image/jpeg")
        self.assertEqual(cover.status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("cover", args=[activity.pk])).status_code, 404)
        self.assertEqual(self.client.get(activity.image.url).status_code, 404)

    def test_existing_organization_cannot_be_claimed(self):
        response = self.client.post(
            reverse("register_org"),
            {
                "username": "intruder",
                "email": "intruder@example.test",
                "organization": "VERIFIED",
                "website": "https://example.test",
                "password1": "Long-Test-Password!1234",
                "password2": "Long-Test-Password!1234",
            },
        )
        self.assertContains(response, "Questo ente esiste")
        self.assertFalse(User.objects.filter(username="intruder").exists())

    def test_registration_creates_unverified_org(self):
        response = self.client.post(
            reverse("register_org"),
            {
                "username": "new-org",
                "email": "office@example.test",
                "organization": "New association",
                "website": "https://example.test",
                "password1": "Long-Test-Password!1234",
                "password2": "Long-Test-Password!1234",
            },
        )
        self.assertEqual(response.status_code, 302)
        org = Organization.objects.get(name="New association")
        self.assertFalse(org.verified)
        self.assertEqual(org.members.get().username, "new-org")
        self.client.force_login(self.reviewer)
        self.client.post(reverse("verify_org", args=[org.pk]), {"revision": org.revision})
        org.refresh_from_db()
        self.assertTrue(org.verified)

    @patch("hub.middleware.time.time", return_value=1800000000)
    def test_auth_rate_limit(self, clock):
        for _ in range(20):
            response = self.client.post(
                reverse("login"), {"username": "nobody", "password": "incorrect"}
            )
            self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("login"), {})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "900")

    @override_settings(DEBUG=False, DEMO_MODE=True)
    def test_demo_disabled_in_production_even_when_flag_set(self):
        self.assertEqual(self.client.post(reverse("demo_login", args=["ente"])).status_code, 404)

    @override_settings(DEBUG=True, DEMO_MODE=True)
    def test_demo_rejects_remote_access(self):
        self.assertEqual(
            self.client.post(
                reverse("demo_login", args=["ente"]), REMOTE_ADDR="203.0.113.12"
            ).status_code,
            404,
        )
