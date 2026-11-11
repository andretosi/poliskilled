import logging
from smtplib import SMTPException

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST

from .forms import EmailChangeForm, ProfileForm
from .services import (
    InvalidConfirmation,
    confirm_email,
    confirmation_profile,
    email_available,
    profile_for,
    send_confirmation,
)
from .throttle import rate_limited, throttle_response

logger = logging.getLogger(__name__)


def notify_verification(request, user, email):
    try:
        if send_confirmation(user, email):
            messages.info(request, "Controlla la posta: trovi il link per confermare la tua email.")
        else:
            messages.info(
                request, "Invio email non ancora disponibile. Puoi usare subito l’account."
            )
    except (SMTPException, OSError):
        logger.warning("Account confirmation email provider unavailable.")
        messages.warning(
            request, "La mail non è partita. Puoi riprovare dalle impostazioni account."
        )
    except InvalidConfirmation:
        messages.warning(request, "L'account è cambiato durante l'invio. Ricarica e riprova.")


@login_required
@require_http_methods(["GET", "POST"])
@sensitive_post_parameters("current_password")
def profile(request):
    account = profile_for(request.user)
    action = request.POST.get("action") if request.method == "POST" else None
    if action == "email" and rate_limited(request, "email-send", request.user.pk):
        return throttle_response()
    form = ProfileForm(request.POST if action == "profile" else None, instance=request.user)
    email_form = EmailChangeForm(request.POST if action == "email" else None, user=request.user)
    if action == "profile" and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error("username", "Questo nome utente è già usato. Scegline un altro.")
        else:
            messages.success(request, "Impostazioni salvate.")
            return redirect("accounts:profile")
    elif action == "email" and email_form.is_valid():
        if not email_available():
            email_form.add_error(None, "Invio email non ancora disponibile. Riprova più avanti.")
        else:
            notify_verification(request, request.user, email_form.cleaned_data["email"])
            return redirect("accounts:profile")
    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "email_form": email_form,
            "account": account,
            "email_available": email_available(),
        },
    )


@login_required
@require_POST
def resend_confirmation(request):
    if rate_limited(request, "email-send", request.user.pk):
        return throttle_response()
    account = profile_for(request.user)
    email = account.pending_email or (account.email if not account.email_verified_at else None)
    if email:
        notify_verification(request, request.user, email)
    return redirect("accounts:profile")


@require_http_methods(["GET", "POST"])
def email_confirm(request, token):
    if rate_limited(request, "email-confirm"):
        return throttle_response()
    valid = True
    try:
        confirmation_profile(token)
        if request.method == "POST":
            confirm_email(token)
            return render(request, "accounts/email_confirm.html", {"confirmed": True})
    except (InvalidConfirmation, IntegrityError):
        valid = False
    return render(request, "accounts/email_confirm.html", {"validlink": valid})
