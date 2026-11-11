from functools import wraps

from django.contrib.auth import views as auth
from django.urls import path, reverse_lazy
from django.views.decorators.cache import never_cache

from . import recovery, views
from .password_forms import PasswordChangeForm

app_name = "accounts"


def private(view):
    @never_cache
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        # Browsers may send Origin: null for form navigation under no-referrer,
        # which correctly fails Django CSRF. Keep same-origin POSTs usable.
        response["Referrer-Policy"] = "same-origin"
        return response

    return wrapped


urlpatterns = [
    path("account/", private(views.profile), name="profile"),
    path("account/email/invia/", private(views.resend_confirmation), name="email_resend"),
    path("account/email/conferma/<str:token>/", private(views.email_confirm), name="email_confirm"),
    path(
        "account/password/cambia/",
        private(
            auth.PasswordChangeView.as_view(
                form_class=PasswordChangeForm,
                template_name="accounts/password_change.html",
                success_url=reverse_lazy("accounts:password_change_done"),
            )
        ),
        name="password_change",
    ),
    path(
        "account/password/cambiata/",
        private(
            auth.PasswordChangeDoneView.as_view(template_name="accounts/password_change_done.html")
        ),
        name="password_change_done",
    ),
    path(
        "account/password/recupera/",
        private(recovery.PasswordResetView.as_view()),
        name="password_reset",
    ),
    path(
        "account/password/richiesta/",
        private(recovery.PasswordResetDoneView.as_view()),
        name="password_reset_done",
    ),
    path(
        "account/password/reimposta/<uidb64>/<token>/",
        private(recovery.PasswordResetConfirmView.as_view()),
        name="password_reset_confirm",
    ),
    path(
        "account/password/ripristinata/",
        private(
            auth.PasswordResetCompleteView.as_view(
                template_name="accounts/password_reset_complete.html"
            )
        ),
        name="password_reset_complete",
    ),
]
