import time
from ipaddress import ip_address

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils.crypto import salted_hmac

from .models import AuthThrottle


def client_address(request):
    peer = request.META.get("REMOTE_ADDR", "")
    if settings.TRUST_LOCAL_PROXY and peer in {"127.0.0.1", "::1"}:
        try:
            return str(ip_address(request.META.get("HTTP_X_REAL_IP", "")))
        except ValueError:
            pass
    return peer


class AuthThrottleMiddleware:
    """Database backed limit, shared by workers; never trusts forwarded IP headers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == "POST" and request.path in {
            "/accedi/",
            "/registrati/",
            "/registrati/ente/",
            "/admin/login/",
        }:
            window = int(time.time()) // 900
            key = salted_hmac("auth-rate", client_address(request)).hexdigest()
            with transaction.atomic():
                record, _ = AuthThrottle.objects.select_for_update().get_or_create(
                    key=key, defaults={"window": window}
                )
                record.count = record.count + 1 if record.window == window else 1
                record.window = window
                record.save()
                AuthThrottle.objects.filter(window__lt=window - 1).delete()
            if record.count > 20:
                response = HttpResponse("Troppi tentativi. Riprova fra 15 minuti.", status=429)
                response["Retry-After"] = "900"
                return response
        return None


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/admin/"):
            response["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
                "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
            )
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.user.is_authenticated or request.path.startswith(("/accedi/", "/registrati/")):
            response["Cache-Control"] = "no-store"
        return response
