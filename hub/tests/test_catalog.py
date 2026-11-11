from django.core.management import call_command
from django.test import override_settings

from hub.models import Activity, Organization, Track, TrackStep

from .base import HubTestCase


class CatalogTests(HubTestCase):
    def test_search_and_type_filter(self):
        Activity.objects.filter(pk=self.activity.pk).update(status="published")
        self.assertContains(self.client.get("/?q=robotics&tipo=project"), "Test robotics")
        self.assertNotContains(self.client.get("/?q=robotics&tipo=course"), "Test robotics")
        self.assertContains(self.client.get("/?q=no-such-result"), "Nessuna attività trovata")
        self.org.short_name = "AEA"
        self.org.save()
        self.assertContains(self.client.get("/?q=AEA&tipo=project"), "Test robotics")

    def test_track_hides_unpublished_activities(self):
        track = Track.objects.create(slug="test", title="Test path")
        TrackStep.objects.create(track=track, activity=self.activity)
        response = self.client.get("/percorsi/test/")
        self.assertContains(response, "Test path")
        self.assertNotContains(response, "Test robotics")

    def test_pages_render(self):
        for path in ["/", "/enti/", "/percorsi/", "/accedi/", "/registrati/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.client.force_login(self.owner)
        for path in ["/dashboard/", "/proposte/nuova/", self.activity.get_absolute_url()]:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    @override_settings(DEBUG=True, DEMO_MODE=True)
    def test_seed_is_idempotent_and_preserves_edits(self):
        call_command("seed_demo", verbosity=0)
        self.assertFalse(Organization.objects.filter(name="Passion in Action").exists())
        passion = Activity.objects.get(seed_key="demo-activity-7")
        self.assertEqual(passion.program, "passion")
        self.assertEqual(
            list(passion.organizations.values_list("name", flat=True)), ["Politecnico di Milano"]
        )
        count = Activity.objects.count()
        item = Activity.objects.get(title="AEA Academy")
        item.description = "An edited description"
        item.save()
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Activity.objects.count(), count)
        item.refresh_from_db()
        self.assertEqual(item.description, "An edited description")
