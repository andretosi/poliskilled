import logging

from django.db import OperationalError
from django.utils import timezone

from .audience import (
    browser_identity,
    eligible_request,
    mark_response,
    public_activities,
    record_view,
)

logger = logging.getLogger(__name__)


class AudienceMiddleware:
    """Count only successful public HTML pages, never private pages or assets."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        match = request.resolver_match
        if (
            request.method != "GET"
            or response.status_code != 200
            or not match
            or match.url_name not in {"home", "activity", "tracks", "track"}
            or not response.get("Content-Type", "").startswith("text/html")
            or not eligible_request(request)
        ):
            return response
        try:
            targets = ["site"]
            if match.url_name == "activity":
                pk = match.kwargs.get("pk")
                if not public_activities().filter(pk=pk).exists():
                    return response
                targets.append(f"activity:{pk}")
            now = timezone.localtime()
            digest, signed = browser_identity(request, now.date())
            mark_response(response, signed, now)
            for target in targets:
                record_view(target, digest, now)
        except OperationalError:
            # A transient counter-store failure must not take down the public catalogue.
            logger.warning("Audience counters temporarily unavailable")
        return response
