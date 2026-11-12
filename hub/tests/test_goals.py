from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone

from hub.models import Activity
from hub.skill_graph import build_goal
from hub.tests.base import HubTestCase


class GoalTests(HubTestCase):
    def test_closed_recurring_courses_stay_in_the_tree_with_a_reopening_notice(self):
        course = self.node("Recurring course", kind="course", availability="closed")
        target = self.node("Future project", [course])
        response = self.client.get(target.get_absolute_url())
        self.assertContains(response, 'data-reopening="true"')
        self.assertContains(
            response,
            '<span class="node-availability node-reopening">Riapertura da verificare</span>',
            count=1,
            html=True,
        )
        self.assertContains(response, "Iscrizioni chiuse")
        self.assertContains(self.client.get(reverse("home")), "Riapertura da verificare")
        self.assertContains(self.client.get(course.get_absolute_url()), "Riapertura da verificare")

    def test_confirmed_open_edition_is_not_marked_pending_until_its_deadline(self):
        course = self.node("Open edition", kind="course", availability="open")
        self.assertFalse(course.reopening_pending)
        course.enrollment_deadline = timezone.now() - timedelta(minutes=1)
        self.assertTrue(course.reopening_pending)
        course.enrollment_deadline = None
        course.ends_on = date(2000, 1, 1)
        self.assertTrue(course.reopening_pending)

    def test_unknown_courses_and_continuous_materials_do_not_imply_reopening(self):
        for availability in ("unknown", "ongoing"):
            course = self.node(availability, kind="course", availability=availability)
            self.assertFalse(course.reopening_pending)
        event = self.node("Closed event", kind="event", availability="closed")
        self.assertFalse(event.reopening_pending)

    def test_dates_show_closed_status_even_without_catalog_stamp_or_explicit_availability(self):
        target = self.node("Finished event", kind="event", ends_on=date(2000, 1, 1))
        self.assertContains(self.client.get(target.get_absolute_url()), "Attività conclusa")
        self.assertContains(self.client.get(reverse("home")), "Attività conclusa")

    def node(self, title, parents=(), **kwargs):
        activity = Activity.objects.create(
            title=title, creator=self.owner, status=kwargs.pop("status", "published"), **kwargs
        )
        activity.organizations.add(self.org)
        activity.predecessors.set(parents)
        return activity

    def test_goal_contains_only_target_and_transitive_public_preparation(self):
        start = self.node("Start")
        parallel = self.node("Parallel")
        middle = self.node("Middle", [start])
        target = self.node("Target course", [middle, parallel], kind="course")
        unrelated = self.node("Unrelated", [start])
        hidden = self.node("Private prerequisite", status="pending")
        target.predecessors.add(hidden)
        stages = build_goal(target)
        ids = {step["activity"].pk for stage in stages for step in stage["steps"]}
        self.assertEqual(ids, {start.pk, parallel.pk, middle.pk, target.pk})
        self.assertNotIn(unrelated.pk, ids)
        self.assertTrue(stages[-1]["steps"][0]["goal"])
        self.assertEqual(len(stages), 3)
        response = self.client.get(target.get_absolute_url())
        self.assertContains(response, f'data-node="{start.pk}"')
        self.assertContains(response, f'data-node="{target.pk}"')
        self.assertNotContains(response, hidden.title)
        self.assertNotContains(response, unrelated.title)

    def test_any_activity_can_be_a_goal_without_invented_prerequisites(self):
        target = self.node("Standalone event", kind="event")
        stages = build_goal(target)
        self.assertEqual(len(stages), 1)
        self.assertEqual(len(stages[0]["steps"]), 1)
        response = self.client.get(target.get_absolute_url())
        self.assertContains(response, "Nessuna preparazione collegata")
        self.assertContains(response, "Salva obiettivo")

    def test_private_goal_and_legacy_track_routes_do_not_disclose_proposals(self):
        target = self.node("Private goal", status="pending")
        self.assertEqual(build_goal(target), [])
        self.assertEqual(self.client.get(target.get_absolute_url()).status_code, 404)
        self.assertRedirects(self.client.get(reverse("tracks")), reverse("home"))

    def test_proposal_uses_only_predecessors_without_named_track(self):
        self.node("Available prerequisite")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("propose"))
        self.assertNotContains(response, 'name="tracks"')
        self.assertContains(response, 'name="predecessors"')
