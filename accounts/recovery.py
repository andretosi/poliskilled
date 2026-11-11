import logging
from smtplib import SMTPException
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy

from .models import AccountProfile, normalize_email
from .password_forms import SetPasswordForm
from .services import email_available, profile_for
from .throttle import rate_limited, throttle_response

logger = logging.getLogger(__name__)


class AccountPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        email = normalize_email(email)
        # Accounts created through createsuperuser/UserAdmin also support recovery.
        candidates = [
            user
            for user in get_user_model()
            .objects.filter(is_active=True, accountprofile__isnull=True)
            .exclude(email="")
            if normalize_email(user.email) == email
        ]
        if len(candidates) > 1 or (
            candidates and AccountProfile.objects.filter(email=email).exists()
        ):
            return
        for user in candidates:
            if user.has_usable_password():
                try:
                    profile_for(user)
                except IntegrityError:
                    continue
        for profile in AccountProfile.objects.select_related("user").filter(
            email=email, user__is_active=True
        ):
            # A direct admin/import edit must not send an account token to an unsynced address.
            if profile.user.has_usable_password() and profile.user.email == profile.email:
                yield profile.user

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = "".join(render_to_string(subject_template_name, context).splitlines())
        body = render_to_string(email_template_name, context)
        EmailMultiAlternatives(subject, body, from_email, [to_email]).send(fail_silently=False)


class PasswordResetView(auth_views.PasswordResetView):
    form_class = AccountPasswordResetForm
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")

    def get_context_data(self, **kwargs):
        return super().get_context_data(email_available=email_available(), **kwargs)

    def post(self, request, *args, **kwargs):
        email = normalize_email(request.POST.get("email", ""))
        if rate_limited(request, "password-reset", email):
            return throttle_response()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        if not email_available():
            return self.render_to_response(self.get_context_data(form=form))
        origin = urlsplit(settings.POLISKILLED_PUBLIC_URL)
        try:
            form.save(
                domain_override=origin.netloc,
                use_https=origin.scheme == "https",
                from_email=settings.DEFAULT_FROM_EMAIL,
                token_generator=self.token_generator,
                email_template_name=self.email_template_name,
                subject_template_name=self.subject_template_name,
                extra_email_context={"public_url": settings.POLISKILLED_PUBLIC_URL.rstrip("/")},
            )
        except (SMTPException, OSError):
            # Same response for unknown accounts and provider failures; no addresses or secrets.
            logger.warning("Password recovery email provider unavailable.")
        return HttpResponseRedirect(self.get_success_url())


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = SetPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST" and rate_limited(request, "password-confirm"):
            return throttle_response()
        return super().dispatch(request, *args, **kwargs)


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(email_available=email_available(), **kwargs)
