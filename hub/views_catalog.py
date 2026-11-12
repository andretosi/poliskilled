from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Case, Q, Value, When
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .forms import CommentForm
from .models import Activity, Organization
from .permissions import can_edit, can_read, can_review, is_reviewer
from .skill_graph import build_goal


@require_GET
def home(request):
    activities = (
        Activity.objects.filter(status=Activity.Status.PUBLISHED)
        .prefetch_related("organizations")
        .order_by(
            Case(
                When(kind="project", then=Value(0)),
                When(kind="course", then=Value(1)),
                default=Value(2),
            ),
            "title",
            "pk",
        )
    )
    query = request.GET.get("q", "").strip()[:120]
    kind = request.GET.get("tipo", "")
    tag = request.GET.get("tag", "")
    if query:
        activities = activities.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(organizations__name__icontains=query)
            | Q(organizations__short_name__icontains=query)
        ).distinct()
    if kind in Activity.Kind.values:
        activities = activities.filter(kind=kind)
    if tag in {"technology", "community"}:
        activities = activities.filter(**{tag: True})
    page = Paginator(activities, 12).get_page(request.GET.get("page"))
    filters = request.GET.copy()
    filters.pop("page", None)
    return render(
        request,
        "hub/home.html",
        {
            "activities": page,
            "page": page,
            "filter_query": filters.urlencode(),
            "query": query,
            "kind": kind,
            "tag": tag,
            "count": page.paginator.count,
        },
    )


@require_GET
def detail(request, pk):
    activity = get_object_or_404(Activity.objects.prefetch_related("organizations"), pk=pk)
    if not can_read(request.user, activity):
        raise Http404
    private = can_edit(request.user, activity) or is_reviewer(request.user)
    stages, graph_error = [], False
    if activity.status == "published":
        try:
            stages = build_goal(activity)
        except ValidationError:
            graph_error = True
    return render(
        request,
        "hub/detail.html",
        {
            "activity": activity,
            "can_edit": can_edit(request.user, activity),
            "can_review": can_review(request.user, activity),
            "private": private,
            "stages": stages,
            "graph_error": graph_error,
            "entries": activity.entries.select_related("author") if private else [],
            "comment_form": CommentForm(),
            "following": activity.successors.filter(status="published").order_by("title"),
        },
    )


@require_GET
def cover(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    if not can_read(request.user, activity) or not activity.image:
        raise Http404
    try:
        response = FileResponse(activity.image.open("rb"), content_type="image/jpeg")
    except FileNotFoundError:
        raise Http404 from None
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
def organizations(request):
    return render(
        request,
        "hub/organizations.html",
        {
            "organizations": Organization.objects.filter(
                Q(verified=True) | ~Q(catalog_source_url="")
            ).prefetch_related("members")
        },
    )


@require_GET
def tracks(request, slug=None):
    return redirect("home")
