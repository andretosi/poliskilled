from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ActivityForm, CommentForm
from .models import Activity, ReviewEntry
from .permissions import can_edit, is_reviewer, owned_activities
from .proposal_service import save_proposal


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    return render(
        request,
        "hub/dashboard.html",
        {
            "activities": owned_activities(request.user).prefetch_related("organizations"),
            "organizations": request.user.organizations.all(),
            "can_propose": request.user.organizations.filter(verified=True).exists(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit(request, pk=None):
    activity = get_object_or_404(Activity, pk=pk) if pk else Activity(creator=request.user)
    if pk and not can_edit(request.user, activity):
        raise Http404
    if not request.user.organizations.filter(verified=True).exists():
        messages.error(request, "Il tuo ente deve essere verificato prima di proporre attività.")
        return redirect("dashboard")
    form = ActivityForm(
        request.POST or None, request.FILES or None, instance=activity, user=request.user
    )
    if request.method == "POST" and form.is_valid():
        intent = request.POST.get("intent", "draft")
        saved = save_proposal(form, request.user, intent, pk)
        if saved:
            messages.success(
                request,
                "Proposta inviata in revisione."
                if intent == "submit"
                else "Bozza salvata. Puoi inviarla quando è pronta.",
            )
            return redirect(saved)
    return render(request, "hub/proposal_form.html", {"form": form, "activity": activity})


@login_required
@require_POST
def comment(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    if not (can_edit(request.user, activity) or is_reviewer(request.user)):
        raise PermissionDenied
    form = CommentForm(request.POST)
    if form.is_valid():
        ReviewEntry.objects.create(
            activity=activity,
            author=request.user,
            action="Commento",
            body=form.cleaned_data["body"],
            revision=activity.revision,
        )
        messages.success(request, "Commento aggiunto.")
    else:
        messages.error(request, "Scrivi un commento da 1 a 3000 caratteri.")
    return redirect(activity.get_absolute_url() + "#discussion")
