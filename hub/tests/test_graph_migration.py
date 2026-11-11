import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase


class GraphMigrationTests(SimpleTestCase):
    def test_historical_upgrade_and_atomic_cycle_rollback(self):
        for scenario in ["valid", "cycle"]:
            with self.subTest(scenario=scenario):
                result = subprocess.run(
                    [sys.executable, "scripts/check_graph_upgrade.py", scenario],
                    cwd=settings.BASE_DIR,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
