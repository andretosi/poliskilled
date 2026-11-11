from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from accounts.views import notify_verification

from .account_forms import OrganizationRequestForm, PersonalRegisterForm
from .forms import RegisterForm
from .models import Organization


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("progress")
    form = PersonalRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            form.add_error(None, "Nome utente o email già presente. Controlla i dati.")
        else:
            login(request, user)
            notify_verification(request, user, user.email)
            return redirect("progress")
    return render(request, "hub/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register_org(request):
    existing = request.user.is_authenticated
    form_class = OrganizationRequestForm if existing else RegisterForm
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = request.user if existing else form.save()
                org = Organization.objects.create(
                    name=form.cleaned_data["organization"], website=form.cleaned_data["website"]
                )
                org.members.add(user)
        except IntegrityError:
            form.add_error(
                None, "Nome utente, email o ente già presente. Riprova con un nome diverso."
            )
        else:
            login(request, user)
            if not existing:
                notify_verification(request, user, user.email)
            messages.success(
                request, "Account creato. Un moderatore verificherà l'identità del tuo ente."
            )
            return redirect("dashboard")
    return render(request, "hub/register.html", {"form": form, "organization_signup": True})


@require_POST
def demo_login(request, role):
    # Demo identities only. Disabled in production even with POLISKILLED_DEMO=1.
    if not settings.DEMO_MODE or not settings.DEBUG:
        raise Http404
    if request.META.get("REMOTE_ADDR") not in {"127.0.0.1", "::1"}:
        raise Http404
    usernames = {"ente": "demo-aea", "moderatore": "demo-moderatore", "studente": "demo-studente"}
    if role not in usernames:
        raise Http404
    user = get_object_or_404(User, username=usernames[role], is_active=True)
    if user.has_usable_password():
        raise Http404
    login(request, user)
    return redirect(
        {"moderatore": "review_queue", "ente": "dashboard", "studente": "progress"}[role]
    )
