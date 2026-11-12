from django.core.exceptions import ValidationError
from django.urls import reverse

from hub.forms import ActivityForm
from hub.models import Activity, Track
from hub.skill_graph import build_goal, build_track, validate_predecessors

from .base import HubTestCase


class SkillGraphTests(HubTestCase):
    def setUp(self):
        self.track = Track.objects.create(slug="dynamic", title="Dynamic")
        self.activity.status = "published"
        self.activity.save()
        self.activity.tracks.add(self.track)

    def add(self, title, parents=(), status="published"):
        item = Activity.objects.create(title=title, creator=self.owner, status=status)
        item.predecessors.set(parents)
        return item

    def test_new_project_generates_levels_and_imports_public_ancestors(self):
        previous = self.activity
        for number in range(5):
            previous = self.add(f"Step {number}", [previous])
        previous.tracks.add(self.track)
        stages = build_track(self.track)
        self.assertEqual(len(stages), 6)
        self.assertEqual(stages[-1]["steps"][0]["activity"], previous)
        self.assertEqual(
            stages[-1]["steps"][0]["parents"],
            list(previous.predecessors.values_list("pk", flat=True)),
        )

    def test_parallel_branches_only_use_actual_edges(self):
        first = self.add("A", [self.activity])
        second = self.add("B")
        first.tracks.add(self.track)
        second.tracks.add(self.track)
        stages = build_track(self.track)
        roots = {node["activity"].pk for node in stages[0]["steps"]}
        self.assertEqual(roots, {self.activity.pk, second.pk})
        self.assertEqual(stages[1]["steps"][0]["parents"], [self.activity.pk])

    def test_pending_nodes_and_their_edges_are_not_exposed(self):
        hidden = self.add("Secret course", status="pending")
        self.activity.predecessors.add(hidden)
        hidden.tracks.add(self.track)
        response = self.client.get(self.activity.get_absolute_url())
        self.assertNotContains(response, hidden.title)
        self.assertNotContains(response, f'data-node="{hidden.pk}"')
        self.assertContains(response, self.activity.title)

    def test_cycles_are_rejected_even_through_unpublished_nodes(self):
        intermediate = self.add("Hidden", [self.activity], status="pending")
        end = self.add("Published", [intermediate])
        with self.assertRaises(ValidationError):
            validate_predecessors(self.activity.pk, [end.pk])
        with self.assertRaises(ValidationError):
            validate_predecessors(self.activity.pk, [self.activity.pk])

    def test_proposal_form_validates_cycles_and_icon_choices(self):
        descendant = self.add("Descendant", [self.activity])
        form = ActivityForm(
            self.payload(predecessors=[descendant.pk], tracks=[self.track.pk]),
            instance=self.activity,
            user=self.owner,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("predecessors", form.errors)
        form = ActivityForm(self.payload(icon="arbitrary"), instance=self.activity, user=self.owner)
        self.assertFalse(form.is_valid())
        self.assertIn("icon", form.errors)

    def test_approved_new_project_appears_without_manual_layout(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("propose"),
            self.payload(
                title="New graph project",
                revision=0,
                tracks=[self.track.pk],
                predecessors=[self.activity.pk],
                icon="robot",
            ),
        )
        self.assertEqual(response.status_code, 302)
        new = Activity.objects.get(title="New graph project")
        self.client.logout()
        self.assertEqual(self.client.get(new.get_absolute_url()).status_code, 404)
        self.client.force_login(self.reviewer)
        self.client.post(
            reverse("decide", args=[new.pk]), {"decision": "approve", "revision": new.revision}
        )
        response = self.client.get(new.get_absolute_url())
        self.assertContains(response, new.title)
        self.assertContains(response, f'data-node="{new.pk}"')
        self.assertEqual(build_goal(new)[1]["steps"][0]["activity"], new)

    def test_unpublished_existing_predecessor_survives_an_edit_without_disclosing_its_title(self):
        hidden = self.add("Private revised title", status="pending")
        self.activity.predecessors.add(hidden)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("edit_proposal", args=[self.activity.pk]))
        self.assertNotContains(response, hidden.title)
        response = self.client.post(
            reverse("edit_proposal", args=[self.activity.pk]),
            self.payload(tracks=[self.track.pk], icon="circuit"),
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.activity.predecessors.filter(pk=hidden.pk).exists())
        self.assertNotIn(hidden.title, self.activity.entries.last().snapshot["predecessors"])

    def test_graph_authority_is_rechecked_inside_the_writer_transaction(self):
        predecessor = self.add("Public")
        form = ActivityForm(
            self.payload(predecessors=[predecessor.pk]), instance=self.activity, user=self.owner
        )
        self.assertTrue(form.is_valid(), form.errors)
        predecessor.status = "pending"
        predecessor.save()
        from hub.proposal_service import save_proposal

        self.assertIsNone(save_proposal(form, self.owner, "submit", self.activity.pk))
        self.assertIn("predecessors", form.errors)

    def test_manual_track_creation_is_retired(self):
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.post("/gestione/percorsi/nuovo/", {}).status_code, 404)

    def test_revoked_cohost_is_not_silently_dropped(self):
        from hub.proposal_service import save_proposal

        form = ActivityForm(
            self.payload(organizations=[self.org.pk, self.partner.pk]),
            instance=self.activity,
            user=self.owner,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.partner.verified = False
        self.partner.save()
        self.assertIsNone(save_proposal(form, self.owner, "submit", self.activity.pk))
        self.assertIn("organizations", form.errors)

    def test_hidden_predecessor_republished_after_validation_does_not_get_deleted(self):
        from hub.proposal_service import save_proposal

        hidden = self.add("Hidden during editing", status="pending")
        self.activity.predecessors.add(hidden)
        form = ActivityForm(self.payload(), instance=self.activity, user=self.owner)
        self.assertTrue(form.is_valid(), form.errors)
        hidden.status = "published"
        hidden.save()
        self.assertIsNone(save_proposal(form, self.owner, "submit", self.activity.pk))
        self.assertTrue(self.activity.predecessors.filter(pk=hidden.pk).exists())

    def test_old_form_without_graph_baseline_cannot_erase_migrated_links(self):
        data = self.payload()
        data.pop("graph_baseline")
        form = ActivityForm(data, instance=self.activity, user=self.owner)
        self.assertFalse(form.is_valid())
        self.assertIn("Ricarica", str(form.non_field_errors()))

    def test_deliberately_empty_choices_can_remove_visible_links(self):
        from hub.proposal_service import save_proposal

        predecessor = self.add("Visible")
        self.activity.predecessors.add(predecessor)
        form = ActivityForm(self.payload(predecessors=[]), instance=self.activity, user=self.owner)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNotNone(save_proposal(form, self.owner, "draft", self.activity.pk))
        self.assertFalse(self.activity.predecessors.exists())

    def test_rendered_choices_and_baseline_use_the_same_visibility_snapshot(self):
        predecessor = self.add("Visible when opened")
        self.activity.predecessors.add(predecessor)
        form = ActivityForm(instance=self.activity, user=self.owner)
        baseline = form.initial["graph_baseline"]
        predecessor.status = "pending"
        predecessor.title = "Private revised title"
        predecessor.save()
        rendered = str(form["predecessors"])
        self.assertIn("Visible when opened", rendered)
        self.assertNotIn("Private revised title", rendered)
        self.assertRegex(rendered, rf'value="{predecessor.pk}"[^>]* checked')
        predecessor.status = "published"
        predecessor.save()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("edit_proposal", args=[self.activity.pk]),
            self.payload(graph_baseline=baseline, predecessors=[predecessor.pk]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.activity.predecessors.filter(pk=predecessor.pk).exists())
