from django.contrib.auth.models import User
from django.template import Context, Template
from django.test import RequestFactory
from django.utils import timezone

from hub.models import Activity, ActivityProgress, Organization
from hub.tests.base import HubTestCase
from insights.models import ActivityInterest, DailyMetric, MonthlyMetric
from insights.reports import goal_report, month_offset
from insights.templatetags.insights_tags import interest_button


class ReportTests(HubTestCase):
    def test_activity_and_goal_pagers_preserve_each_others_position(self):
        for index in range(35):
            Activity.objects.create(title=f"Goal {index}", creator=self.owner, status="published")
        self.client.force_login(self.reviewer)
        response = self.client.get(self.url, {"page": 2, "obiettivi": 2})
        self.assertContains(response, "page=1&amp;obiettivi=2")
        self.assertContains(response, "obiettivi=3&amp;page=2")

    def test_goal_report_queries_do_not_grow_with_goal_count(self):
        for index in range(20):
            item = Activity.objects.create(
                title=f"Goal {index}", status="published", creator=self.owner
            )
            item.predecessors.add(self.activity)
        with self.assertNumQueries(5):
            rows = goal_report(Activity.objects.all(), reviewer=True)
        self.assertEqual(len(rows), 21)

    def test_interest_buttons_share_request_local_queries(self):
        request = RequestFactory().get("/percorsi/")
        request.user = self.owner
        with self.assertNumQueries(2):
            for _ in range(20):
                result = interest_button({"request": request}, self.activity)
                self.assertTrue(result["visible"])

    def setUp(self):
        self.url = "/risultati/"
        self.activity.status = "published"
        self.activity.save()
        self.student = User.objects.create_user("private-person", email="secret@example.test")
        self.foreign = Activity.objects.create(
            title="Other entity secret draft", creator=self.other, status="draft"
        )
        self.foreign.organizations.add(self.partner)

    def test_only_reviewers_and_verified_members_have_access(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        pending = Organization.objects.create(name="Pending verification")
        pending.members.add(self.student)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_calendar_total_obeys_month_status_and_organization_scope(self):
        now = timezone.now()
        self.activity.starts_at = now
        self.activity.save()
        self.foreign.starts_at = now
        self.foreign.save()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).context["scheduled_count"], 1)
        previous = month_offset(timezone.localdate().replace(day=1), -1).strftime("%Y-%m")
        self.assertEqual(
            self.client.get(self.url, {"mese": previous}).context["scheduled_count"], 0
        )
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(self.url).context["scheduled_count"], 1)
        self.foreign.status = "published"
        self.foreign.save()
        self.assertEqual(self.client.get(self.url).context["scheduled_count"], 2)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_org_scope_rechecks_membership_and_does_not_expose_other_entities(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertContains(response, self.activity.title)
        self.assertNotContains(response, self.foreign.title)
        self.assertEqual(self.client.get(self.url, {"ente": self.partner.pk}).status_code, 404)
        self.assertEqual(self.client.get(self.url, {"ente": "bad"}).status_code, 404)
        self.assertEqual(
            self.client.get(self.url, {"ente": "99999999999999999999"}).status_code, 404
        )

    def test_owned_drafts_and_historical_metrics_remain_visible(self):
        self.activity.status = "draft"
        self.activity.save()
        today = timezone.localdate()
        DailyMetric.objects.create(date=today, target=f"activity:{self.activity.pk}", views=7)
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertContains(response, self.activity.title)
        self.assertContains(response, "Bozza")
        self.assertEqual(response.context["view_count"], 7)
        self.assertEqual(response.context["published_count"], 0)

    def test_multiorg_activities_and_people_are_counted_once(self):
        self.partner.members.add(self.owner)
        self.activity.organizations.add(self.partner)
        second = Activity.objects.create(title="Second", creator=self.owner, status="published")
        second.organizations.add(self.org, self.partner)
        for activity in (self.activity, second):
            ActivityInterest.objects.create(user=self.student, activity=activity)
            ActivityProgress.objects.create(user=self.student, activity=activity)
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.context["activity_count"], 3)
        self.assertEqual(response.context["published_count"], 2)
        self.assertEqual(response.context["interested_count"], 1)
        self.assertEqual(response.context["completed_count"], 1)
        self.assertEqual(len(response.context["activity_rows"]), 3)
        selected = self.client.get(self.url, {"ente": self.org.pk})
        self.assertEqual(selected.context["activity_count"], 2)

    def test_reviewer_sees_all_statuses_and_entity_sees_only_global_visitor_total(self):
        today = timezone.localdate()
        MonthlyMetric.objects.create(month=today.replace(day=1), target="site", visitors=42)
        DailyMetric.objects.create(date=today, target="site", views=80)
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.context["site_visitors"], 42)
        self.assertNotIn("site_chart", response.context)
        self.assertNotIn("site_views", response.context)
        self.client.force_login(self.reviewer)
        response = self.client.get(self.url)
        self.assertContains(response, self.foreign.title)
        self.assertEqual(response.context["site_views"], 80)
        self.assertIn("site_chart", response.context)

    def test_no_participant_identity_or_edit_action_is_rendered(self):
        ActivityInterest.objects.create(user=self.student, activity=self.activity)
        ActivityProgress.objects.create(user=self.student, activity=self.activity)
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertNotContains(response, self.student.username)
        self.assertNotContains(response, self.student.email)
        self.assertNotContains(response, f"/proposte/{self.activity.pk}/modifica/")
        self.assertNotContains(response, f"/revisione/{self.activity.pk}/decisione/")
        self.assertIn("no-store", response["Cache-Control"])

    def test_track_includes_public_ancestors_without_foreign_engagement(self):
        self.foreign.status = "published"
        self.foreign.save()
        self.foreign.predecessors.add(self.activity)
        ActivityInterest.objects.create(user=self.student, activity=self.activity)
        ActivityProgress.objects.create(user=self.student, activity=self.activity)
        ActivityInterest.objects.create(user=self.other, activity=self.foreign)
        ActivityInterest.objects.create(user=self.owner, activity=self.foreign)
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        row = next(row for row in response.context["goal_rows"] if row["goal"] == self.foreign)
        self.assertEqual(row["activities"], 1)
        self.assertEqual(row["followers"], 2)
        self.assertEqual(row["engaged"], 1)
        self.client.force_login(self.reviewer)
        response = self.client.get(self.url)
        self.assertEqual(
            next(row for row in response.context["goal_rows"] if row["goal"] == self.foreign)[
                "engaged"
            ],
            3,
        )

    def test_month_filter_rejects_invalid_or_out_of_retention_bounds(self):
        self.client.force_login(self.owner)
        for value in ("nonsense", "1900-01", "9999-01", "2026-13", "2026-11-01"):
            self.assertEqual(self.client.get(self.url, {"mese": value}).status_code, 400, value)
        self.assertEqual(
            self.client.get(self.url, {"mese": timezone.localdate().strftime("%Y-%m")}).status_code,
            200,
        )

    def test_personal_saved_lists_exclude_private_activities_and_other_accounts(self):
        ActivityInterest.objects.create(user=self.owner, activity=self.activity)
        ActivityInterest.objects.create(user=self.owner, activity=self.foreign)
        request = RequestFactory().get("/progressi/")
        request.user = self.owner
        rendered = Template("{% load insights_tags %}{% saved_intents %}").render(
            Context({"request": request})
        )
        self.assertIn(self.activity.title, rendered)
        self.assertNotIn(self.foreign.title, rendered)
        request.user = self.student
        rendered = Template("{% load insights_tags %}{% saved_intents %}").render(
            Context({"request": request})
        )
        self.assertNotIn(self.activity.title, rendered)
