import json

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from hub.models import Activity, Organization

from .base import HubTestCase


class PersonalProgressTests(HubTestCase):
    def setUp(self):
        self.activity.status = "published"
        self.activity.save()
        self.url = "/api/progress/"

    def write(self, payload):
        if isinstance(payload, dict) and "revision" not in payload:
            payload["revision"] = self.client.get(self.url).json().get("revision", 0)
        return self.client.post(self.url, json.dumps(payload), content_type="application/json")

    def test_personal_registration_needs_no_organization(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "student",
                "email": "student@example.test",
                "password1": "Personal-Test-Password!1234",
                "password2": "Personal-Test-Password!1234",
            },
        )
        self.assertRedirects(response, "/progressi/")
        user = User.objects.get(username="student")
        self.assertFalse(user.organizations.exists())
        self.assertFalse(user.has_perm("hub.review_activity"))

    def test_anonymous_api_requires_login_and_csrf(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.assertEqual(self.write({"changes": {str(self.activity.pk): True}}).status_code, 401)
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.owner)
        response = browser.post(self.url, "{}", content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_import_is_idempotent_and_progress_is_private(self):
        self.client.force_login(self.owner)
        for _ in range(2):
            response = self.write({"import": [self.activity.pk], "changes": {}})
            self.assertEqual(response.json()["completed"], [self.activity.pk])
        self.assertEqual(response["Cache-Control"], "no-store")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).json()["completed"], [])
        self.assertNotContains(self.client.get("/progressi/"), self.activity.title)

    def test_undo_does_not_erase_other_completions(self):
        second = Activity.objects.create(title="Second", creator=self.owner, status="published")
        self.client.force_login(self.owner)
        self.write({"import": [self.activity.pk, second.pk]})
        response = self.write({"changes": {str(self.activity.pk): False}})
        self.assertEqual(response.json()["completed"], [second.pk])

    def test_old_tab_cannot_write_to_a_newly_selected_account(self):
        self.client.force_login(self.other)
        for header in ["HTTP_X_POLISKILLED_USER", "HTTP_X_RAMO_USER"]:
            with self.subTest(header=header):
                response = self.client.post(
                    self.url,
                    json.dumps({"import": [self.activity.pk]}),
                    content_type="application/json",
                    **{header: str(self.owner.pk)},
                )
                self.assertEqual(response.status_code, 409)
                self.assertEqual(self.client.get(self.url).json()["completed"], [])

    def test_both_brand_headers_accept_the_current_account(self):
        self.client.force_login(self.owner)
        for header in ["HTTP_X_POLISKILLED_USER", "HTTP_X_RAMO_USER"]:
            revision = self.client.get(self.url).json()["revision"]
            response = self.client.post(
                self.url,
                json.dumps({"revision": revision, "import": [self.activity.pk]}),
                content_type="application/json",
                **{header: str(self.owner.pk)},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["completed"], [self.activity.pk])

    def test_private_and_missing_activities_cannot_be_imported(self):
        self.activity.status = "draft"
        self.activity.save()
        self.client.force_login(self.owner)
        response = self.write({"import": [self.activity.pk, 987654]})
        self.assertEqual(response.json()["completed"], [])
        self.assertEqual(response.json()["imported"], [])
        response = self.write({"changes": {str(self.activity.pk): True}})
        self.assertEqual(response.json()["applied"], [])
        response = self.write({"changes": {str(self.activity.pk): False}})
        self.assertEqual(response.json()["applied"], [self.activity.pk])

    def test_existing_progress_survives_moderation_and_can_be_removed(self):
        self.client.force_login(self.owner)
        self.write({"import": [self.activity.pk]})
        self.activity.status = "pending"
        self.activity.save()
        self.assertEqual(self.client.get(self.url).json()["completed"], [self.activity.pk])
        self.assertNotContains(self.client.get("/progressi/"), self.activity.title)
        self.assertEqual(
            self.write({"changes": {str(self.activity.pk): False}}).json()["completed"], []
        )

    def test_malformed_payloads_fail_without_writes(self):
        self.client.force_login(self.owner)
        for payload in [
            [],
            {"user": self.other.pk},
            {"import": [True]},
            {"changes": {str(self.activity.pk): "yes"}},
            {"import": list(range(201))},
        ]:
            self.assertEqual(self.write(payload).status_code, 400, payload)
        self.assertEqual(
            self.client.post(self.url, "{", content_type="application/json").status_code, 400
        )
        self.assertEqual(self.client.get(self.url).json()["completed"], [])

    def test_existing_personal_account_can_request_an_unverified_organization(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            "/registrati/ente/",
            {
                "organization": "New personal association",
                "website": "https://example.test",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        org = Organization.objects.get(name="New personal association")
        self.assertFalse(org.verified)
        self.assertEqual(org.members.get(), self.owner)

    def test_late_post_cannot_overwrite_a_newer_acknowledged_undo(self):
        self.client.force_login(self.owner)
        old_revision = self.client.get(self.url).json()["revision"]
        self.write({"changes": {str(self.activity.pk): False}})
        response = self.write(
            {
                "revision": old_revision,
                "changes": {str(self.activity.pk): True},
            }
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "progress_conflict")
        self.assertEqual(self.client.get(self.url).json()["completed"], [])
