import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hub.catalog_import import import_catalog


class Command(BaseCommand):
    help = "Importa il catalogo verificato; nessun account di enti viene creato."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(settings.BASE_DIR / "data/catalog/current.json"))
        parser.add_argument("--archive-demo", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            data = json.loads(Path(options["file"]).read_text())
            with transaction.atomic():
                result = import_catalog(data, archive_demo=options["archive_demo"])
                if options["dry_run"]:
                    transaction.set_rollback(True)
        except (OSError, ValueError, KeyError, ValidationError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps(result))
        if options["dry_run"]:
            self.stdout.write("Simulazione: nessuna modifica salvata.")
