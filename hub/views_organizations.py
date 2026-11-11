from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .models import Organization
from .organization_forms import OrganizationForm
from .organization_service import save_organization
from .permissions import is_reviewer


@login_required
@require_GET
def my_organizations(request):
    return render(
        request,
        "hub/my_organizations.html",
        {
            "organizations": request.user.organizations.all(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit_organization(request, pk):
    organization = get_object_or_404(Organization, pk=pk)
    if not organization.members.filter(pk=request.user.pk).exists():
        raise PermissionDenied
    form = OrganizationForm(
        request.POST if request.method == "POST" else None,
        request.FILES or None,
        instance=organization,
        initial={"revision": organization.revision},
    )
    # Decode bounded uploads before acquiring SQLite's single writer lock.
    if request.method == "POST" and form.is_valid():
        try:
            saved = save_organization(form, request.user)
        except IntegrityError:
            form.add_error("name", "Un ente con questo nome esiste già.")
        else:
            if saved:
                messages.success(
                    request,
                    "Ente aggiornato." if saved.verified else "Richiesta inviata ai gestori.",
                )
                return redirect("my_organizations")
    return render(
        request,
        "hub/organization_form.html",
        {
            "form": form,
            "organization": organization,
        },
    )


@require_GET
def logo(request, pk):
    organization = get_object_or_404(Organization, pk=pk)
    private_access = request.user.is_authenticated and (
        is_reviewer(request.user) or organization.members.filter(pk=request.user.pk).exists()
    )
    if not organization.logo or not (organization.verified or private_access):
        raise Http404
    try:
        response = FileResponse(organization.logo.open("rb"), content_type="image/png")
    except FileNotFoundError:
        raise Http404 from None
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
