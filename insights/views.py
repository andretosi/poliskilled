import logging

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import OperationalError
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .audience import (
    COOKIE_NAME,
    browser_identity,
    eligible_request,
    public_activities,
    record_view,
)
from .models import AnalyticsState, DailyMetric, MonthlyMetric
from .reports import (
    activity_report,
    chart_points,
    goal_report,
    month_offset,
    permitted_scope,
    selected_month,
)

logger = logging.getLogger(__name__)


@never_cache
@require_GET
@login_required
def dashboard(request):
    activities, organizations, organization, reviewer = permitted_scope(
        request.user, request.GET.get("ente")
    )
    try:
        month = selected_month(request.GET.get("mese"))
    except ValueError as exc:
        return render(request, "insights/invalid_filter.html", {"error": str(exc)}, status=400)
    context = activity_report(activities, month)
    context["activity_rows"] = Paginator(context["activity_rows"], 30).get_page(
        request.GET.get("page")
    )
    site = MonthlyMetric.objects.filter(month=month, target="site").first()
    context.update(
        month=month,
        month_value=month.strftime("%Y-%m"),
        min_month=month_offset(timezone.localdate().replace(day=1), -23).strftime("%Y-%m"),
        max_month=timezone.localdate().strftime("%Y-%m"),
        organizations=organizations,
        selected_organization=organization,
        global_report=reviewer,
        site_visitors=site.visitors if site else 0,
        activation=AnalyticsState.objects.filter(key="audience").first(),
        goal_rows=Paginator(
            goal_report(activities, reviewer and organization is None), 12
        ).get_page(request.GET.get("obiettivi")),
    )
    if reviewer and organization is None:
        site_daily = DailyMetric.objects.filter(
            date__gte=month, date__lt=month_offset(month, 1), target="site"
        )
        context["site_views"] = site_daily.aggregate(total=Sum("views"))["total"] or 0
        context["site_chart"] = chart_points(month, dict(site_daily.values_list("date", "views")))
    return render(request, "insights/dashboard.html", context)


@never_cache
@require_POST
def activity_view(request, pk):
    # Dialog opens count exactly like public detail pages; IDs are never trusted.
    get_object_or_404(public_activities(), pk=pk)
    if not eligible_request(request) or COOKIE_NAME not in request.COOKIES:
        return HttpResponse(status=204)
    now = timezone.localtime()
    digest, rotated = browser_identity(request, now.date())
    if rotated:
        # Only public HTML responses can establish or renew the monthly browser cookie.
        return HttpResponse(status=204)
    try:
        record_view(f"activity:{pk}", digest, now)
    except OperationalError:
        logger.warning("Audience counters temporarily unavailable")
        return JsonResponse({"recorded": False}, status=202)
    return HttpResponse(status=204)
