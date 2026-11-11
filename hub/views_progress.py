import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from .models import Activity, ActivityProgress, ProgressRevision


def parse_progress(body):
    if len(body) > 20000:
        raise ValueError
    data = json.loads(body)
    if not isinstance(data, dict) or data.keys() - {"import", "changes", "revision"}:
        raise ValueError
    revision = data.get("revision")
    if type(revision) is not int or not 0 <= revision < 2**63 - 1:
        raise ValueError
    imported, changes = data.get("import", []), data.get("changes", {})
    if not isinstance(imported, list) or not isinstance(changes, dict):
        raise ValueError
    if len(imported) > 200 or len(changes) > 200:
        raise ValueError
    if any(type(pk) is not int or not 0 < pk < 2**63 for pk in imported):
        raise ValueError
    if any(
        not key.isascii()
        or not key.isdigit()
        or not 0 < int(key) < 2**63
        or type(value) is not bool
        for key, value in changes.items()
    ):
        raise ValueError
    return set(imported), {int(key): value for key, value in changes.items()}, revision


@never_cache
@require_http_methods(["GET", "POST"])
def progress_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Accedi per sincronizzare."}, status=401)
    client_user = request.headers.get(
        "X-PoliSkilled-User", request.headers.get("X-Ramo-User", str(request.user.pk))
    )
    if client_user != str(request.user.pk):
        return JsonResponse({"error": "Account cambiato. Ricarica la pagina."}, status=409)
    imported, applied = set(), set()
    if request.method == "POST":
        try:
            incoming, changes, expected = parse_progress(request.body)
        except (ValueError, TypeError, UnicodeDecodeError):
            return JsonResponse({"error": "Dati dei progressi non validi."}, status=400)
    with transaction.atomic():
        state = ProgressRevision.objects.filter(user=request.user).first()
        if request.method == "POST":
            state, _ = ProgressRevision.objects.select_for_update().get_or_create(user=request.user)
            if state.revision != expected:
                return JsonResponse({"code": "progress_conflict"}, status=409)
            wanted = incoming | {pk for pk, done in changes.items() if done}
            visible = set(
                Activity.objects.filter(pk__in=wanted, status="published").values_list(
                    "pk", flat=True
                )
            )
            imported = incoming & visible
            applied = {pk for pk, done in changes.items() if not done or pk in visible}
            for pk in visible:
                ActivityProgress.objects.get_or_create(user=request.user, activity_id=pk)
            ActivityProgress.objects.filter(
                user=request.user,
                activity_id__in=[pk for pk, done in changes.items() if not done],
            ).delete()
            state.revision += 1
            state.save(update_fields=["revision"])
        completed = list(
            ActivityProgress.objects.filter(user=request.user)
            .order_by("activity_id")
            .values_list("activity_id", flat=True)
        )
        revision = state.revision if state else 0
    return JsonResponse(
        {
            "completed": completed,
            "revision": revision,
            "imported": sorted(imported),
            "applied": sorted(applied),
        }
    )


@require_GET
@login_required
def progress_page(request):
    completed = list(
        ActivityProgress.objects.filter(user=request.user).values_list("activity_id", flat=True)
    )
    activities = Activity.objects.filter(status="published", pk__in=completed).prefetch_related(
        "organizations"
    )
    return render(
        request,
        "hub/progress.html",
        {
            "activities": activities,
            "progress_snapshot": completed,
        },
    )
