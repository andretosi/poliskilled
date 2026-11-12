import json

from django.test import Client

from hub.models import Track
from hub.tests.base import HubTestCase
from insights.models import ActivityInterest, TrackFollow


class EngagementTests(HubTestCase):
    def test_interest_requires_at_least_one_verified_or_catalogued_organizer(self):
        self.activity.status = "published"
        self.activity.save()
        self.activity.organizations.clear()
        self.client.force_login(self.owner)
        url = f"/api/interessi/{self.activity.pk}/"
        self.assertEqual(self.client.post(url, {"active": "true"}).status_code, 404)
        self.org.verified = False
        self.org.catalog_source_url = "https://example.test/catalogued"
        self.org.save()
        self.activity.organizations.add(self.org, self.partner)
        self.assertEqual(self.client.post(url, {"active": "true"}).status_code, 200)
        self.assertEqual(ActivityInterest.objects.count(), 1)

    def test_delayed_guest_import_cannot_resurrect_an_acknowledged_undo(self):
        self.activity.status = "published"
        self.activity.save()
        self.client.force_login(self.owner)
        payload = {
            "interests": [self.activity.pk],
            "markers": {
                "interests": {str(self.activity.pk): "1:original"},
            },
        }

        def post_import():
            return self.client.post(
                "/api/intenti/importa/", json.dumps(payload), content_type="application/json"
            )

        post_import()
        self.client.post(f"/api/interessi/{self.activity.pk}/", {"active": "false"})
        response = post_import()
        self.assertFalse(ActivityInterest.objects.exists())
        self.assertEqual(response.json()["acknowledged"]["interests"], [self.activity.pk])
        payload["markers"]["interests"][str(self.activity.pk)] = "1:new-save"
        post_import()
        self.assertTrue(ActivityInterest.objects.filter(user=self.owner).exists())

    def test_interest_import_is_private_and_idempotent(self):
        self.activity.status = "published"
        self.activity.save()
        self.client.force_login(self.owner)
        data = json.dumps({"interests": [self.activity.pk], "follows": []})
        for _ in range(2):
            response = self.client.post(
                "/api/intenti/importa/", data, content_type="application/json"
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(ActivityInterest.objects.count(), 1)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get("/api/intenti/").json()["interests"], [])

    def test_private_activity_cannot_receive_interest(self):
        self.client.force_login(self.owner)
        response = self.client.post(f"/api/interessi/{self.activity.pk}/", {"active": "true"})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ActivityInterest.objects.exists())

    def test_mutations_require_authentication_post_and_csrf(self):
        url = f"/api/interessi/{self.activity.pk}/"
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {"active": "true"}).status_code, 401)
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.owner)
        self.assertEqual(browser.post(url, {"active": "true"}).status_code, 403)

    def test_follow_toggle_is_idempotent_and_only_changes_current_account(self):
        track = Track.objects.create(title="Track", slug="track")
        url = f"/api/percorsi/{track.pk}/segui/"
        self.client.force_login(self.other)
        self.client.post(url, {"active": "true"})
        self.client.force_login(self.owner)
        for _ in range(2):
            self.assertEqual(self.client.post(url, {"active": "true"}).status_code, 200)
        self.assertEqual(TrackFollow.objects.count(), 2)
        for _ in range(2):
            self.assertEqual(self.client.post(url, {"active": "false"}).status_code, 200)
        self.assertEqual(TrackFollow.objects.get().user, self.other)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {"active": "yes"}).status_code, 400)

    def test_import_rejects_invalid_ids_and_ignores_private_objects(self):
        self.client.force_login(self.owner)
        url = "/api/intenti/importa/"
        for data in (
            [],
            {"user": 4},
            {"interests": [True]},
            {"follows": [-1]},
            {"interests": list(range(201))},
        ):
            response = self.client.post(url, json.dumps(data), content_type="application/json")
            self.assertEqual(response.status_code, 400, data)
        response = self.client.post(
            url,
            json.dumps({"interests": [self.activity.pk, 123456789]}),
            content_type="application/json",
        )
        self.assertEqual(response.json()["interests"], [])
        self.assertFalse(ActivityInterest.objects.exists())

    def test_unverified_activities_and_stale_account_headers_are_rejected(self):
        self.activity.status = "published"
        self.activity.save()
        self.org.verified = False
        self.org.save()
        self.client.force_login(self.owner)
        url = f"/api/interessi/{self.activity.pk}/"
        self.assertEqual(self.client.post(url, {"active": "true"}).status_code, 404)
        self.assertEqual(
            self.client.post(
                url, {"active": "true"}, HTTP_X_POLISKILLED_USER=str(self.other.pk)
            ).status_code,
            409,
        )
