from copy import deepcopy
from datetime import date

from django.core.exceptions import ValidationError
from django.urls import reverse

from hub.catalog_import import import_catalog
from hub.models import Activity, ActivityProgress, Organization
from hub.skill_graph import graph_baseline
from hub.tests.base import HubTestCase


class CatalogImportTests(HubTestCase):
    def payload_catalog(self):
        return {
            "reviewed_on": "2026-11-12",
            "organizations": [
                {
                    "key": "polimi",
                    "name": "Politecnico di Milano",
                    "website": "https://www.polimi.it/",
                    "source_url": "https://www.polimi.it/",
                }
            ],
            "activities": [
                {
                    "key": "source-course",
                    "title": "Real course",
                    "kind": "course",
                    "organization_keys": ["polimi"],
                    "description": "A sourced course.",
                    "source_url": "https://www.polimi.it/course",
                    "availability": "closed",
                },
                {
                    "key": "source-project",
                    "title": "Real project",
                    "kind": "project",
                    "organization_keys": ["polimi"],
                    "description": "A sourced project.",
                    "source_url": "https://www.polimi.it/project",
                    "availability": "ongoing",
                    "predecessor_keys": ["source-course"],
                    "preparation_notes": "Editorial advice.",
                },
            ],
        }

    def test_import_is_idempotent_and_never_claims_entity_accounts(self):
        data = self.payload_catalog()
        import_catalog(data)
        goal = Activity.objects.get(title="Real project")
        revision = goal.revision
        import_catalog(data)
        goal.refresh_from_db()
        self.assertEqual(goal.revision, revision)
        self.assertEqual(goal.predecessors.get().title, "Real course")
        self.assertEqual(goal.source_checked_on, date(2026, 11, 12))
        self.assertFalse(goal.creator.is_active)
        self.assertFalse(goal.creator.has_usable_password())
        org = Organization.objects.get(name="Politecnico di Milano")
        self.assertFalse(org.verified)
        self.assertFalse(org.members.exists())
        self.assertContains(self.client.get("/enti/"), org.name)
        self.assertContains(self.client.get(goal.get_absolute_url()), "Editorial advice.")

    def test_bad_edge_or_cycle_rolls_back_the_whole_import(self):
        for target in ("missing", "source-project"):
            data = self.payload_catalog()
            data["activities"][0]["predecessor_keys"] = [target]
            with self.assertRaises(ValidationError):
                import_catalog(data)
            self.assertFalse(Activity.objects.filter(title="Real course").exists())

    def test_renamed_organization_keeps_identity_members_and_activity_attribution(self):
        data = self.payload_catalog()
        import_catalog(data)
        org = Organization.objects.get(name="Politecnico di Milano")
        org.members.add(self.owner)
        org.name = "Locally renamed organization"
        org.catalog_source_url = ""
        org.save()
        count = Organization.objects.count()
        import_catalog(data)
        self.assertEqual(Organization.objects.count(), count)
        self.assertTrue(org.members.filter(pk=self.owner.pk).exists())
        self.assertEqual(Activity.objects.get(title="Real course").organizations.get().pk, org.pk)
        org.refresh_from_db()
        self.assertEqual(org.name, "Locally renamed organization")
        self.assertEqual(org.catalog_source_url, "")

    def test_dates_keep_the_same_signature_after_database_timezone_conversion(self):
        data = self.payload_catalog()
        data["activities"][0]["starts_at"] = "2026-11-20T18:00:00+01:00"
        import_catalog(data)
        self.assertEqual(import_catalog(data)["preserved"], 0)
        data["activities"][0]["starts_at"] = "2026-11-21T18:00:00+01:00"
        result = import_catalog(data)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["preserved"], 0)
        course = Activity.objects.get(title="Real course")
        self.assertEqual(course.starts_at.day, 21)

    def test_valid_edge_reversal_is_checked_against_final_batch_not_old_links(self):
        data = self.payload_catalog()
        import_catalog(data)
        data["activities"][0]["predecessor_keys"] = ["source-project"]
        data["activities"][1]["predecessor_keys"] = []
        self.assertEqual(import_catalog(data)["updated"], 2)
        course = Activity.objects.get(title="Real course")
        project = Activity.objects.get(title="Real project")
        self.assertEqual(course.predecessors.get(), project)
        self.assertFalse(project.predecessors.exists())

    def test_existing_link_to_a_locally_pending_parent_survives_import(self):
        data = self.payload_catalog()
        import_catalog(data)
        parent = Activity.objects.get(title="Real course")
        parent.status = "pending"
        parent.save()
        result = import_catalog(data)
        self.assertEqual(result["preserved"], 1)
        child = Activity.objects.get(title="Real project")
        self.assertEqual(child.predecessors.get(), parent)
        self.assertNotContains(self.client.get(child.get_absolute_url()), parent.title)
        new = deepcopy(data["activities"][1])
        new.update(key="new-child", title="New child")
        data["activities"].append(new)
        with self.assertRaises(ValidationError):
            import_catalog(data)
        self.assertFalse(Activity.objects.filter(title="New child").exists())

    def test_organizer_can_update_imported_calendar_and_republish(self):
        data = self.payload_catalog()
        data["activities"][0].update(period="Old edition", ends_on="2026-01-01")
        import_catalog(data)
        course = Activity.objects.get(title="Real course")
        org = course.organizations.get()
        org.verified = True
        org.save()
        org.members.add(self.owner)
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("edit_proposal", args=[course.pk]),
            self.payload(
                title=course.title,
                kind="course",
                organizations=[org.pk],
                revision=course.revision,
                graph_baseline=graph_baseline(course),
                starts_at="2099-02-10T18:00",
                period="New edition in February 2099",
                ends_on="2099-02-20",
                enrollment_deadline="2099-02-01T12:00",
                availability="open",
                official_requirements="Updated prerequisites",
            ),
        )
        self.assertEqual(response.status_code, 302)
        course.refresh_from_db()
        self.assertIsNone(course.source_checked_on)
        self.assertEqual(course.status, "pending")
        self.client.force_login(self.reviewer)
        self.client.post(
            reverse("decide", args=[course.pk]),
            {"decision": "approve", "revision": course.revision},
        )
        self.client.logout()
        response = self.client.get(course.get_absolute_url())
        self.assertContains(response, "New edition in February 2099")
        self.assertContains(response, "Iscrizioni aperte")
        self.assertContains(response, "Updated prerequisites")
        self.assertContains(response, "Fine attività")
        self.assertContains(response, "Iscrizioni entro")
        self.assertNotContains(response, "Old edition")
        self.assertNotContains(response, "Fonte verificata il")

    def test_local_edits_are_preserved_and_demo_progress_is_archived_not_reassigned(self):
        data = self.payload_catalog()
        import_catalog(data)
        course = Activity.objects.get(title="Real course")
        course.description = "Local edit"
        course.save()
        changed = deepcopy(data)
        changed["activities"][0]["description"] = "Upstream edit"
        result = import_catalog(changed)
        course.refresh_from_db()
        self.assertEqual(course.description, "Local edit")
        self.assertEqual(result["preserved"], 1)
        self.activity.seed_key = "demo-activity-99"
        self.activity.is_sample = True
        self.activity.status = "published"
        self.activity.save()
        ActivityProgress.objects.create(user=self.owner, activity=self.activity)
        import_catalog(data, archive_demo=True)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, "draft")
        self.assertTrue(
            ActivityProgress.objects.filter(user=self.owner, activity=self.activity).exists()
        )
        self.assertFalse(ActivityProgress.objects.filter(activity=course).exists())
