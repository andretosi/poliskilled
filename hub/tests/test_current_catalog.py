import json

from django.conf import settings
from django.test import TestCase

from hub.catalog_import import import_catalog
from hub.models import Activity, Organization
from hub.skill_graph import build_goal, load_public_graph


class CurrentCatalogTests(TestCase):
    def test_curated_catalog_imports_with_acyclic_sourced_public_goals(self):
        data = json.loads((settings.BASE_DIR / "data/catalog/current.json").read_text())
        result = import_catalog(data)
        self.assertEqual(result["created"], len(data["activities"]))
        self.assertEqual(Organization.objects.count(), len(data["organizations"]))
        graph = load_public_graph()
        for goal in Activity.objects.all():
            with self.subTest(goal=goal.title):
                self.assertTrue(goal.source_url.startswith("https://"))
                self.assertFalse(goal.is_sample)
                self.assertEqual(goal.level, 0)
                self.assertEqual(goal.source_checked_on.isoformat(), data["reviewed_on"])
                stages = build_goal(goal, graph)
                self.assertEqual(stages[-1]["steps"][0]["activity"], goal)
                if goal.predecessors.exists():
                    self.assertTrue(goal.preparation_notes)
        timestamps = list(Activity.objects.values_list("pk", "updated_at"))
        repeated = import_catalog(data)
        self.assertEqual(repeated["updated"], 0)
        self.assertEqual(repeated["preserved"], 0)
        self.assertEqual(list(Activity.objects.values_list("pk", "updated_at")), timestamps)
