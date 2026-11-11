import json
from hashlib import sha256

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from hub.models import Track

from .audience import public_activities
from .models import ActivityInterest, ImportedIntent, TrackFollow


def check_account(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Accedi per sincronizzare."}, status=401)
    if request.headers.get("X-Poliskilled-User", str(request.user.pk)) != str(request.user.pk):
        return JsonResponse({"error": "Account cambiato. Ricarica la pagina."}, status=409)
    return None


def state(user):
    return {
        "interests": list(
            ActivityInterest.objects.filter(user=user, activity__in=public_activities())
            .order_by("activity_id")
            .values_list("activity_id", flat=True)
        ),
        "follows": list(
            TrackFollow.objects.filter(user=user)
            .order_by("track_id")
            .values_list("track_id", flat=True)
        ),
    }


@never_cache
@require_GET
def intent_state(request):
    error = check_account(request)
    return error if error is not None else JsonResponse(state(request.user))


def set_intent(request, model, field, target):
    active = request.POST.get("active")
    if active not in {"true", "false"}:
        return JsonResponse({"error": "Scelta non valida."}, status=400)
    lookup = {"user": request.user, field: target}
    if active == "true":
        model.objects.get_or_create(**lookup)
    else:
        model.objects.filter(**lookup).delete()
    return JsonResponse({"active": active == "true"})


@never_cache
@require_POST
def activity_interest(request, pk):
    error = check_account(request)
    if error is not None:
        return error
    activity = get_object_or_404(public_activities(), pk=pk)
    return set_intent(request, ActivityInterest, "activity", activity)


@never_cache
@require_POST
def track_follow(request, pk):
    error = check_account(request)
    if error is not None:
        return error
    return set_intent(request, TrackFollow, "track", get_object_or_404(Track, pk=pk))


def parse_import(body):
    if len(body) > 60000:
        raise ValueError
    data = json.loads(body)
    if not isinstance(data, dict) or data.keys() - {"interests", "follows", "markers"}:
        raise ValueError
    markers = data.get("markers", {})
    if not isinstance(markers, dict) or markers.keys() - {"interests", "follows"}:
        raise ValueError
    for name in ("interests", "follows"):
        values = data.get(name, [])
        if not isinstance(values, list) or len(values) > 200:
            raise ValueError
        if any(type(pk) is not int or not 0 < pk < 2**63 for pk in values):
            raise ValueError
        saved = markers.get(name, {})
        if not isinstance(saved, dict) or len(saved) > 200:
            raise ValueError
        for pk, marker in saved.items():
            if pk not in {str(value) for value in values} or not isinstance(marker, str):
                raise ValueError
            if not 1 <= len(marker) <= 96:
                raise ValueError
    return data


@never_cache
@require_POST
def import_intents(request):
    error = check_account(request)
    if error is not None:
        return error
    try:
        data = parse_import(request.body)
    except (ValueError, TypeError, UnicodeDecodeError):
        return JsonResponse({"error": "Preferenze non valide."}, status=400)
    acknowledged = {"interests": [], "follows": []}
    with transaction.atomic():
        for kind, objects, model, field in (
            ("interests", public_activities(), ActivityInterest, "activity"),
            ("follows", Track.objects.all(), TrackFollow, "track"),
        ):
            markers = data.get("markers", {}).get(kind, {})
            for target in objects.filter(pk__in=data.get(kind, [])):
                marker = markers.get(str(target.pk), "1")
                fingerprint = sha256(f"{kind}:{target.pk}:{marker}".encode()).hexdigest()
                _, fresh = ImportedIntent.objects.get_or_create(
                    user=request.user, fingerprint=fingerprint
                )
                if fresh:
                    model.objects.get_or_create(user=request.user, **{field: target})
                acknowledged[kind].append(target.pk)
    return JsonResponse({**state(request.user), "acknowledged": acknowledged})
