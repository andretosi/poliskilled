import time

from django.db import transaction
from django.http import HttpResponse
from django.utils.crypto import salted_hmac

from hub.middleware import client_address
from hub.models import AuthThrottle


def rate_limited(request, namespace, target="", limit=5):
    # Same units as hub.middleware: its shared cleanup must not delete these records.
    window = int(time.time()) // 900
    keys = [("ip", client_address(request), 20)]
    if target:
        keys.append(("target", str(target), limit))
    blocked = False
    with transaction.atomic():
        for kind, value, maximum in keys:
            key = salted_hmac(f"accounts:{namespace}:{kind}", value).hexdigest()
            record, _ = AuthThrottle.objects.select_for_update().get_or_create(
                key=key, defaults={"window": window}
            )
            record.count = record.count + 1 if record.window == window else 1
            record.window = window
            record.save()
            blocked = blocked or record.count > maximum
        AuthThrottle.objects.filter(window__lt=window - 1).delete()
    return blocked


def throttle_response():
    response = HttpResponse("Troppi tentativi. Riprova fra 15 minuti.", status=429)
    response["Retry-After"] = "900"
    return response
