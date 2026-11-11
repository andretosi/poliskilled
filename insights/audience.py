"""First-party browser estimates. No account, network or device data are persisted."""

import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.crypto import salted_hmac

from hub.models import Activity

from .models import AnalyticsState, DailyAudience, DailyMetric, MonthlyAudience, MonthlyMetric

COOKIE_NAME = "poliskilled_audience"
COOKIE_SALT = "insights.monthly-browser.v1"
BOT = re.compile(r"bot|crawler|spider|slurp|headless|preview|facebookexternalhit", re.I)


def public_activities():
    return Activity.objects.filter(status="published", organizations__verified=True).distinct()


def eligible_request(request):
    return not (
        BOT.search(request.headers.get("User-Agent", ""))
        or "prefetch" in request.headers.get("Purpose", "").lower()
        or "prefetch" in request.headers.get("Sec-Purpose", "").lower()
        or "prerender" in request.headers.get("Sec-Purpose", "").lower()
        or request.headers.get("Sec-Fetch-Site") == "cross-site"
    )


def browser_identity(request, today):
    """Rotate random, signed cookie each calendar month; only return HMAC to storage."""
    month = today.strftime("%Y-%m")
    signed = request.COOKIES.get(COOKIE_NAME)
    payload = None
    if signed:
        try:
            payload = signing.loads(signed, salt=COOKIE_SALT, max_age=32 * 86400)
        except (signing.BadSignature, ValueError, TypeError):
            pass
    valid = (
        isinstance(payload, dict)
        and payload.get("month") == month
        and isinstance(payload.get("token"), str)
        and re.fullmatch(r"[0-9a-f]{64}", payload["token"])
    )
    if not valid:
        payload = {"month": month, "token": secrets.token_hex(32)}
        signed = signing.dumps(payload, salt=COOKIE_SALT)
    digest = salted_hmac(
        "insights.browser-digest.v1", f"{month}:{payload['token']}", algorithm="sha256"
    ).hexdigest()
    return digest, signed if not valid else None


def mark_response(response, signed, now):
    # Applies even when no cookie is rotated: no personalized Set-Cookie or counters in caches.
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ["Cookie"])
    if signed:
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        response.set_cookie(
            COOKIE_NAME,
            signed,
            max_age=max(1, int((next_month - now).total_seconds())),
            secure=not settings.DEBUG,
            httponly=True,
            samesite="Lax",
        )


def record_view(target, digest, now):
    """Atomic dedup of repeats within 30 seconds; counters survive browser-data cleanup."""
    today = timezone.localdate(now)
    month = today.replace(day=1)
    with transaction.atomic():
        AnalyticsState.objects.get_or_create(key="audience", defaults={"activated_on": today})
        visitor, new_day = DailyAudience.objects.get_or_create(
            date=today, target=target, digest=digest, defaults={"last_seen": now}
        )
        if not new_day:
            accepted = DailyAudience.objects.filter(
                pk=visitor.pk, last_seen__lte=now - timedelta(seconds=30)
            ).update(last_seen=now)
            if not accepted:
                return False
        monthly, new_month = MonthlyAudience.objects.get_or_create(
            month=month, target=target, digest=digest, defaults={"last_seen": today}
        )
        if not new_month and monthly.last_seen != today:
            MonthlyAudience.objects.filter(pk=monthly.pk).update(last_seen=today)
        metric, _ = DailyMetric.objects.get_or_create(date=today, target=target)
        DailyMetric.objects.filter(pk=metric.pk).update(
            views=F("views") + 1, visitors=F("visitors") + int(new_day)
        )
        if new_month:
            monthly_metric, _ = MonthlyMetric.objects.get_or_create(month=month, target=target)
            MonthlyMetric.objects.filter(pk=monthly_metric.pk).update(visitors=F("visitors") + 1)
    return True
