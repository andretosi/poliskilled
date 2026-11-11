from django.conf import settings
from django.db import models


class ImportedIntent(models.Model):
    """Consumed guest saves stay consumed after an account undo or a late retry."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fingerprint = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "fingerprint"], name="insights_unique_import")
        ]


class ActivityInterest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity = models.ForeignKey("hub.Activity", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "activity"], name="insights_unique_interest")
        ]


class TrackFollow(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    track = models.ForeignKey("hub.Track", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "track"], name="insights_unique_follow")
        ]


class DailyAudience(models.Model):
    date = models.DateField(db_index=True)
    target = models.CharField(max_length=48)
    digest = models.CharField(max_length=64)
    last_seen = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["date", "target", "digest"], name="insights_unique_daily_browser"
            )
        ]


class MonthlyAudience(models.Model):
    month = models.DateField(db_index=True)
    target = models.CharField(max_length=48)
    digest = models.CharField(max_length=64)
    last_seen = models.DateField(db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["month", "target", "digest"], name="insights_unique_monthly_browser"
            )
        ]


class DailyMetric(models.Model):
    date = models.DateField(db_index=True)
    target = models.CharField(max_length=48)
    views = models.PositiveBigIntegerField(default=0)
    visitors = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["date", "target"], name="insights_unique_daily_metric")
        ]


class MonthlyMetric(models.Model):
    month = models.DateField(db_index=True)
    target = models.CharField(max_length=48)
    visitors = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["month", "target"], name="insights_unique_monthly_metric"
            )
        ]


class AnalyticsState(models.Model):
    """One activation marker, independent from retained metric rows."""

    key = models.CharField(primary_key=True, max_length=20, default="audience")
    activated_on = models.DateField()
