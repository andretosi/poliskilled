from collections import defaultdict

from django.conf import settings

from .models import TrackStep
from .permissions import is_reviewer


def site(request):
    user = request.user
    legacy = defaultdict(list)
    for step in TrackStep.objects.filter(activity__status="published").select_related("track"):
        legacy[step.track.slug].append({"step": step.pk, "activity": step.activity_id})
    return {
        "demo_mode": settings.DEMO_MODE,
        "is_reviewer": is_reviewer(user),
        "has_organization": user.is_authenticated and user.organizations.exists(),
        "can_propose": user.is_authenticated and user.organizations.filter(verified=True).exists(),
        "legacy_progress": dict(legacy),
    }
