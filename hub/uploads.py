import logging

from django.core.exceptions import RequestDataTooBig
from django.core.files.uploadhandler import FileUploadHandler
from django.http import HttpResponse

MAX_REQUEST_BYTES = 4 * 1024 * 1024
MAX_FILE_BYTES = 3 * 1024 * 1024
logger = logging.getLogger(__name__)


def delete_cover(storage, name):
    if name:
        try:
            storage.delete(name)
        except OSError:
            logger.exception("Could not remove a superseded cover; storage cleanup needed.")


class RequestSizeMiddleware:
    """Reject declared oversized requests before CSRF parses multipart data."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            size = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            return HttpResponse("Dimensione della richiesta non valida.", status=400)
        if size > MAX_REQUEST_BYTES:
            return HttpResponse("La richiesta supera 4 MB.", status=413)
        return self.get_response(request)


class BoundedUploadHandler(FileUploadHandler):
    """Hard cap while streaming, before Django's memory/temp-file handlers."""

    def __init__(self, request=None):
        super().__init__(request)
        self.received = 0

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > MAX_FILE_BYTES:
            raise RequestDataTooBig("Le immagini non possono superare 3 MB.")
        return raw_data

    def file_complete(self, file_size):
        return None
