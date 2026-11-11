from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .management_service import managers, set_manager
from .models import Activity, ManagementEntry, Organization
from .permissions import is_reviewer


@login_required
@permission_required("hub.review_activity", raise_exception=True)
@require_GET
def overview(request):
    query = request.GET.get("q", "").strip()[:100]
    people = User.objects.filter(is_active=True).order_by("username")
    if query:
        people = people.filter(Q(username__icontains=query) | Q(email__icontains=query))
    else:
        people = managers().filter(is_active=True).order_by("username")
    people = list(people[:30])
    manager_ids = set(managers().values_list("pk", flat=True))
    group_manager_ids = set(
        User.objects.filter(
            groups__permissions__codename="review_activity",
            groups__permissions__content_type__app_label="hub",
        ).values_list("pk", flat=True)
    )
    for person in people:
        person.site_manager = person.pk in manager_ids
        person.group_manager = person.pk in group_manager_ids
        person.role_editable = (
            person.pk != request.user.pk and not person.is_superuser and not person.group_manager
        )
    return render(
        request,
        "hub/management.html",
        {
            "people": people,
            "query": query,
            "pending_count": Activity.objects.filter(status="pending").count(),
            "organizations": Organization.objects.filter(
                verified=False, review_reason=""
            ).prefetch_related("members"),
            "all_organizations": Organization.objects.all(),
            "recent_actions": ManagementEntry.objects.select_related(
                "actor", "subject", "organization"
            )[:12],
        },
    )


@login_required
@require_POST
def role(request, pk):
    if request.POST.get("enabled") not in {"0", "1"} or request.POST.get("expected") not in {
        "0",
        "1",
    }:
        raise PermissionDenied
    get_object_or_404(User, pk=pk)
    try:
        set_manager(
            request.user, pk, request.POST["enabled"] == "1", request.POST["expected"] == "1"
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Ruolo aggiornato.")
    return redirect("management")


@login_required
@require_POST
@transaction.atomic
def organization_decision(request, pk):
    if not is_reviewer(User.objects.get(pk=request.user.pk)):
        raise PermissionDenied
    organization = get_object_or_404(Organization.objects.select_for_update(), pk=pk)
    if organization.members.filter(pk=request.user.pk).exists():
        raise PermissionDenied
    reason = request.POST.get("reason", "").strip()
    action = request.POST.get("decision", "approve")
    if (
        str(organization.revision) != request.POST.get("revision")
        or organization.verified
        or organization.review_reason
    ):
        messages.error(request, "La richiesta è cambiata. Ricarica la pagina.")
    elif (
        action not in {"approve", "changes"}
        or (action == "changes" and not reason)
        or len(reason) > 1500
    ):
        messages.error(
            request, "Per chiedere modifiche, scrivi una motivazione entro 1.500 caratteri."
        )
    else:
        organization.verified = action == "approve"
        organization.review_reason = reason if action == "changes" else ""
        organization.revision += 1
        organization.save(update_fields=["verified", "review_reason", "revision"])
        ManagementEntry.objects.create(
            actor=request.user,
            organization=organization,
            action="Ente approvato" if organization.verified else "Ente da rivedere",
            reason=reason,
        )
        messages.success(
            request,
            "Ente approvato." if organization.verified else "Richiesta di modifiche inviata.",
        )
    return redirect("management")
