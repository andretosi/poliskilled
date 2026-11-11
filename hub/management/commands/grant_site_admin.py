from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Abilita il primo gestore del sito (accesso riservato al responsabile del server)."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, username, **options):
        try:
            user = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            raise CommandError("Account attivo non trovato.") from None
        user.user_permissions.add(
            Permission.objects.get(codename="review_activity", content_type__app_label="hub")
        )
        self.stdout.write(
            self.style.SUCCESS("Gestore abilitato. Nessun accesso Django admin aggiunto.")
        )
