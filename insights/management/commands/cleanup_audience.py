from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from insights.models import DailyAudience, DailyMetric, MonthlyAudience, MonthlyMetric
from insights.reports import month_offset


class Command(BaseCommand):
    help = "Elimina digest oltre 40 giorni e aggregati oltre 24 mesi, in lotti da 1.000."

    def handle(self, *args, **options):
        today = timezone.localdate()
        cutoff = today - timedelta(days=40)
        oldest_month = month_offset(today.replace(day=1), -23)
        queries = [
            DailyAudience.objects.filter(date__lt=cutoff),
            MonthlyAudience.objects.filter(last_seen__lt=cutoff),
            DailyMetric.objects.filter(date__lt=oldest_month),
            MonthlyMetric.objects.filter(month__lt=oldest_month),
        ]
        deleted = 0
        for query in queries:
            while ids := list(query.order_by("pk").values_list("pk", flat=True)[:1000]):
                count, _ = query.model.objects.filter(pk__in=ids).delete()
                deleted += count
        self.stdout.write(f"Eliminate {deleted} righe scadute.")
