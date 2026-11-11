from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core import signing
from django.core.management import call_command
from django.db import OperationalError
from django.test import Client, RequestFactory, override_settings
from django.utils import timezone

from hub.tests.base import HubTestCase
from insights.audience import COOKIE_NAME, COOKIE_SALT, browser_identity, record_view
from insights.models import DailyAudience, DailyMetric, MonthlyAudience, MonthlyMetric


class AudienceTests(HubTestCase):
    def setUp(self):
        self.activity.status = "published"
        self.activity.save()
        self.url = self.activity.get_absolute_url()

    def test_browser_dedup_is_separate_from_account_identity(self):
        self.client.get(self.url)
        self.client.force_login(self.owner)
        self.client.get(self.url)
        self.client.force_login(self.other)
        self.client.get(self.url)
        target = f"activity:{self.activity.pk}"
        self.assertEqual(DailyMetric.objects.get(target=target).views, 1)
        self.assertEqual(MonthlyMetric.objects.get(target=target).visitors, 1)
        self.assertEqual(DailyAudience.objects.filter(target=target).count(), 1)
        browser = Client()
        browser.get(self.url)
        self.assertEqual(MonthlyMetric.objects.get(target=target).visitors, 2)

    def test_repeat_views_daily_and_monthly_reach_are_distinct(self):
        now = datetime(2026, 11, 12, 12, tzinfo=ZoneInfo("Europe/Rome"))
        target = f"activity:{self.activity.pk}"
        self.assertTrue(record_view(target, "a" * 64, now))
        self.assertFalse(record_view(target, "a" * 64, now + timedelta(seconds=2)))
        self.assertTrue(record_view(target, "a" * 64, now + timedelta(seconds=31)))
        self.assertEqual(DailyMetric.objects.get(target=target).views, 2)
        self.assertEqual(DailyMetric.objects.get(target=target).visitors, 1)
        tomorrow = now + timedelta(days=1)
        record_view(target, "a" * 64, tomorrow)
        self.assertEqual(MonthlyMetric.objects.get(target=target).visitors, 1)
        self.assertEqual(DailyMetric.objects.filter(target=target).count(), 2)

    def test_monthly_cookie_rotates_and_only_hmac_is_stored(self):
        factory = RequestFactory()
        now = datetime(2026, 11, 12, tzinfo=ZoneInfo("Europe/Rome"))
        digest, cookie = browser_identity(factory.get("/"), now.date())
        payload = signing.loads(cookie, salt=COOKIE_SALT)
        request = factory.get("/", HTTP_COOKIE=f"{COOKIE_NAME}={cookie}")
        same, no_rotation = browser_identity(request, now.date())
        changed, rotated = browser_identity(request, now.replace(month=12).date())
        self.assertEqual(same, digest)
        self.assertIsNone(no_rotation)
        self.assertNotEqual(changed, digest)
        self.assertIsNotNone(rotated)
        record_view("site", digest, now)
        saved = DailyAudience.objects.get()
        self.assertEqual(saved.digest, digest)
        self.assertNotIn(payload["token"], saved.digest)
        self.assertEqual(len(saved.digest), 64)

    @override_settings(DEBUG=False)
    def test_cookie_attributes_and_no_cache_leak(self):
        response = self.client.get(self.url)
        cookie = response.cookies[COOKIE_NAME]
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("private", response["Cache-Control"])
        self.assertIn("Cookie", response["Vary"])

    def test_excluded_requests_do_not_set_cookie_or_write(self):
        self.client.get(self.url, HTTP_USER_AGENT="Googlebot")
        self.client.get(self.url, HTTP_PURPOSE="prefetch")
        self.client.get(self.url, HTTP_SEC_PURPOSE="prefetch;prerender")
        self.client.head(self.url)
        self.client.get("/accedi/")
        self.client.get("/enti/")
        self.client.get("/non-esiste/")
        self.assertNotIn(COOKIE_NAME, self.client.cookies)
        self.assertFalse(DailyMetric.objects.exists())

    def test_private_and_unverified_activities_never_tracked(self):
        self.client.force_login(self.owner)
        self.activity.status = "draft"
        self.activity.save()
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertNotIn(COOKIE_NAME, self.client.cookies)
        self.assertEqual(
            self.client.post(f"/api/attivita/{self.activity.pk}/visita/").status_code, 404
        )
        self.activity.status = "published"
        self.activity.save()
        self.org.verified = False
        self.org.save()
        self.client.get(self.url)
        self.assertFalse(DailyMetric.objects.exists())

    def test_dialog_post_requires_csrf_and_established_public_cookie(self):
        url = f"/api/attivita/{self.activity.pk}/visita/"
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 204)
        self.assertFalse(DailyMetric.objects.exists())
        self.client.get("/")
        for _ in range(2):
            self.assertEqual(self.client.post(url).status_code, 204)
        self.assertEqual(DailyMetric.objects.get(target=f"activity:{self.activity.pk}").views, 1)
        browser = Client(enforce_csrf_checks=True)
        browser.get("/")
        self.assertEqual(browser.post(url).status_code, 403)

    def test_transient_counter_failure_keeps_public_page_available(self):
        with patch("insights.middleware.record_view", side_effect=OperationalError("locked")):
            self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_partial_failure_preserves_cookie_and_does_not_inflate_site_visitors(self):
        def fail_activity(target, digest, now):
            if target != "site":
                raise OperationalError("locked")
            return record_view(target, digest, now)

        with patch("insights.middleware.record_view", side_effect=fail_activity):
            response = self.client.get(self.url)
        self.assertIn(COOKIE_NAME, response.cookies)
        self.client.get(self.url)
        self.assertEqual(MonthlyMetric.objects.get(target="site").visitors, 1)

    def test_retention_purges_browser_data_but_preserves_recent_aggregates(self):
        now = timezone.localtime()
        old = now - timedelta(days=42)
        record_view("site", "a" * 64, old)
        record_view("site", "b" * 64, now)
        DailyMetric.objects.create(date=now.date().replace(year=now.year - 3), target="expired")
        MonthlyMetric.objects.create(
            month=now.date().replace(year=now.year - 3, day=1), target="expired"
        )
        call_command("cleanup_audience", verbosity=0)
        self.assertFalse(DailyAudience.objects.filter(digest="a" * 64).exists())
        self.assertFalse(MonthlyAudience.objects.filter(digest="a" * 64).exists())
        self.assertTrue(DailyMetric.objects.filter(date=old.date()).exists())
        self.assertFalse(DailyMetric.objects.filter(target="expired").exists())
        self.assertFalse(MonthlyMetric.objects.filter(target="expired").exists())
