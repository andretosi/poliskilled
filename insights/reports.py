from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Sum
from django.http import Http404
from django.utils import timezone

from hub.models import Activity, ActivityProgress, Organization
from hub.permissions import is_reviewer
from hub.skill_graph import build_goal, load_public_graph

from .models import ActivityInterest, DailyMetric, MonthlyMetric


def month_offset(month, offset):
    total = month.year * 12 + month.month - 1 + offset
    return date(total // 12, total % 12 + 1, 1)


def selected_month(value):
    current = timezone.localdate().replace(day=1)
    if not value:
        return current
    try:
        parsed = date.fromisoformat(value + "-01")
    except (ValueError, TypeError):
        raise ValueError("Scegli un mese valido.") from None
    if not month_offset(current, -23) <= parsed <= current:
        raise ValueError("Scegli uno degli ultimi 24 mesi.")
    return parsed


def permitted_scope(user, organization_id):
    reviewer = is_reviewer(user)
    organizations = Organization.objects.all()
    if not reviewer:
        organizations = organizations.filter(members=user, verified=True)
    if not reviewer and not organizations.exists():
        raise PermissionDenied
    activities = Activity.objects.all()
    if not reviewer:
        activities = activities.filter(organizations__in=organizations)
    selected = None
    if organization_id:
        try:
            selected = organizations.get(pk=int(organization_id))
        except (ValueError, Organization.DoesNotExist):
            raise Http404 from None
        activities = activities.filter(organizations=selected)
    return activities.distinct(), organizations, selected, reviewer


def people_count(model, ids):
    return model.objects.filter(activity_id__in=ids).values("user_id").distinct().count()


def engagement_counts(model, ids):
    return dict(
        model.objects.filter(activity_id__in=ids)
        .values("activity_id")
        .annotate(total=Count("user_id", distinct=True))
        .values_list("activity_id", "total")
    )


def activity_report(activities, month):
    rows = list(activities.order_by("title", "pk"))
    ids = [activity.pk for activity in rows]
    targets = [f"activity:{pk}" for pk in ids]
    end = month_offset(month, 1)
    daily = DailyMetric.objects.filter(date__gte=month, date__lt=end, target__in=targets)
    views = dict(daily.values("target").annotate(total=Sum("views")).values_list("target", "total"))
    reach = dict(
        MonthlyMetric.objects.filter(month=month, target__in=targets).values_list(
            "target", "visitors"
        )
    )
    interested = engagement_counts(ActivityInterest, ids)
    completed = engagement_counts(ActivityProgress, ids)
    for activity in rows:
        activity.insight_views = views.get(f"activity:{activity.pk}", 0)
        activity.insight_reach = reach.get(f"activity:{activity.pk}", 0)
        activity.insight_interested = interested.get(activity.pk, 0)
        activity.insight_completed = completed.get(activity.pk, 0)
    rows.sort(
        key=lambda activity: (-activity.insight_views, activity.title.casefold(), activity.pk)
    )
    by_day = dict(daily.values("date").annotate(total=Sum("views")).values_list("date", "total"))
    return {
        "activity_rows": rows,
        "published_count": sum(activity.status == "published" for activity in rows),
        "scheduled_count": activities.filter(
            status="published", starts_at__date__gte=month, starts_at__date__lt=end
        ).count(),
        "activity_count": len(rows),
        "view_count": sum(views.values()),
        "interested_count": people_count(ActivityInterest, ids),
        "completed_count": people_count(ActivityProgress, ids),
        "chart": chart_points(month, by_day),
    }


def chart_points(month, by_day):
    days = monthrange(month.year, month.month)[1]
    maximum = max(by_day.values(), default=0)
    width = 900 / days
    points = []
    for day in range(days):
        current = month + timedelta(days=day)
        value = by_day.get(current, 0)
        height = round(150 * value / max(maximum, 1), 2)
        points.append(
            {
                "date": current,
                "value": value,
                "x": round(day * width + 3, 2),
                "width": round(max(width - 6, 1), 2),
                "y": 160 - height,
                "height": height,
                "label": day == 0 or current.day % 5 == 0 or current.day == days,
            }
        )
    return points


def goal_report(activities, reviewer):
    """Only counts reach templates; each public activity is its own objective."""
    ids = set(activities.values_list("pk", flat=True))
    graph = load_public_graph()
    followers, completed = defaultdict(set), defaultdict(set)
    for model, bucket in ((ActivityInterest, followers), (ActivityProgress, completed)):
        for activity_id, user_id in model.objects.filter(activity_id__in=graph[0]).values_list(
            "activity_id", "user_id"
        ):
            bucket[activity_id].add(user_id)
    rows = []
    for goal in graph[0].values():
        try:
            public_ids = {
                step["activity"].pk for stage in build_goal(goal, graph) for step in stage["steps"]
            }
        except ValidationError:
            continue
        own_ids = public_ids & ids
        if not reviewer and not own_ids:
            continue
        engaged = set()
        for pk in own_ids:
            engaged.update(followers[pk], completed[pk])
        if reviewer:
            engaged.update(followers[goal.pk])
        rows.append(
            {
                "goal": goal,
                "followers": len(followers[goal.pk]),
                "engaged": len(engaged),
                "activities": len(own_ids),
            }
        )
    return sorted(rows, key=lambda row: (-row["followers"], row["goal"].title))
