from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import RequestDataTooBig
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, override_settings
from django.urls import reverse

from hub.models import Activity, Organization
from hub.uploads import BoundedUploadHandler

from .base import HubTestCase


class RegressionTests(HubTestCase):
    def test_file_stream_has_hard_cap(self):
        handler = BoundedUploadHandler()
        chunk = b"x" * (64 * 1024)
        for index in range(48):
            self.assertEqual(handler.receive_data_chunk(chunk, index * len(chunk)), chunk)
        with self.assertRaises(RequestDataTooBig):
            handler.receive_data_chunk(b"x", 3 * 1024 * 1024)

    def test_oversized_multipart_is_rejected_before_login(self):
        browser = Client(enforce_csrf_checks=True)
        browser.get(reverse("login"))
        upload = SimpleUploadedFile("large.jpg", b"x" * (3 * 1024 * 1024 + 1), "image/jpeg")
        response = browser.post(reverse("propose"), {"image": upload})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Activity.objects.count(), 1)

    def test_large_request_rejected_before_body_processing(self):
        response = self.client.post(
            reverse("propose"),
            data=b"",
            content_type="application/octet-stream",
            CONTENT_LENGTH=str(5 * 1024 * 1024),
        )
        self.assertEqual(response.status_code, 413)

    def test_case_insensitive_organization_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Organization.objects.create(name="VERIFIED")

    def test_pagination_reaches_older_records_and_preserves_filters(self):
        Activity.objects.filter(pk=self.activity.pk).update(status="published")
        Activity.objects.bulk_create(
            [
                Activity(
                    title=f"Test newer {index}",
                    description="description",
                    creator=self.owner,
                    kind="project",
                    status="published",
                )
                for index in range(60)
            ]
        )
        response = self.client.get("/?q=Test&tipo=project")
        self.assertContains(response, "Successiva")
        self.assertContains(response, "q=Test&amp;tipo=project&amp;page=2")
        self.assertNotContains(response, "Test robotics")
        self.assertContains(self.client.get("/?q=Test&tipo=project&page=6"), "Test robotics")

    @override_settings(DEBUG=True, DEMO_MODE=True)
    def test_renamed_seed_does_not_reappear(self):
        call_command("seed_demo", stdout=StringIO(), verbosity=0)
        activity = Activity.objects.get(seed_key="demo-activity-2")
        activity.title = "Renamed by the owner"
        activity.save()
        total = Activity.objects.count()
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Activity.objects.count(), total)
        self.assertFalse(Activity.objects.filter(title="AEA Academy").exists())

    def test_demo_guards_with_existing_passwordless_identity(self):
        user = User.objects.create_user(username="demo-aea", password=None)
        self.org.members.add(user)
        endpoint = reverse("demo_login", args=["ente"])
        with override_settings(DEBUG=True, DEMO_MODE=True):
            self.assertEqual(self.client.post(endpoint).status_code, 302)
            self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
            self.client.logout()
            self.assertEqual(
                self.client.post(endpoint, REMOTE_ADDR="203.0.113.12").status_code, 404
            )
            self.assertNotIn("_auth_user_id", self.client.session)
        with override_settings(DEBUG=False, DEMO_MODE=True):
            self.assertEqual(self.client.post(endpoint).status_code, 404)
            self.assertNotIn("_auth_user_id", self.client.session)

    def test_org_verification_requires_independent_reviewer(self):
        self.org.verified = False
        self.org.save()
        endpoint = reverse("verify_org", args=[self.org.pk])
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(endpoint).status_code, 403)
        self.org.members.add(self.reviewer)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.post(endpoint).status_code, 403)
        self.org.refresh_from_db()
        self.assertFalse(self.org.verified)

    def test_reviewer_can_request_changes_for_revoked_org(self):
        self.org.verified = False
        self.org.save()
        self.client.force_login(self.reviewer)
        self.client.post(
            reverse("decide", args=[self.activity.pk]),
            {
                "decision": "changes",
                "reason": "Resolve the organization identity.",
                "revision": 1,
            },
        )
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, "changes")
