from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms import DecisionForm
from .models import Activity, ReviewEntry
from .permissions import can_review


@login_required
@permission_required("hub.review_activity", raise_exception=True)
@require_GET
def review_queue(request):
    pending = Activity.objects.filter(status="pending").prefetch_related("organizations")
    return render(
        request,
        "hub/review_queue.html",
        {
            "activities": pending,
        },
    )


@login_required
@require_POST
@transaction.atomic
def decide(request, pk):
    activity = get_object_or_404(Activity.objects.select_for_update(), pk=pk)
    if not can_review(request.user, activity):
        raise PermissionDenied
    form = DecisionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Per richiedere modifiche serve una motivazione valida.")
    elif (
        activity.status != Activity.Status.PENDING
        or form.cleaned_data["revision"] != activity.revision
    ):
        messages.error(
            request, "La proposta è cambiata o è già stata esaminata. Ricarica la pagina."
        )
    elif (
        form.cleaned_data["decision"] == "approve"
        and activity.organizations.filter(verified=False).exists()
    ):
        messages.error(request, "Tutti gli enti devono essere verificati prima dell'approvazione.")
    else:
        approved = form.cleaned_data["decision"] == "approve"
        activity.status = Activity.Status.PUBLISHED if approved else Activity.Status.CHANGES
        activity.save(update_fields=["status", "updated_at"])
        ReviewEntry.objects.create(
            activity=activity,
            author=request.user,
            revision=activity.revision,
            action="Approvata" if approved else "Modifiche richieste",
            body=form.cleaned_data["reason"],
        )
        messages.success(
            request, "Attività pubblicata." if approved else "Richiesta di modifiche inviata."
        )
    return redirect(activity)
