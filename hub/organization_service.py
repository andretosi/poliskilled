from functools import partial

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms.models import construct_instance
from django.shortcuts import get_object_or_404

from .models import ManagementEntry, Organization
from .uploads import delete_cover


def save_organization(form, user):
    current, old_logo = None, None
    try:
        with transaction.atomic():
            current = get_object_or_404(
                Organization.objects.select_for_update(), pk=form.instance.pk
            )
            if not current.members.filter(pk=user.pk).exists():
                raise PermissionDenied
            if form.cleaned_data["revision"] != current.revision:
                form.add_error(None, "L'ente è cambiato. Ricarica la pagina.")
                return None
            old_logo = current.logo.name
            identity = (current.name, current.website)
            current = construct_instance(form, current, form._meta.fields)
            if identity != (current.name, current.website):
                current.verified = False
            current.review_reason = ""
            current.revision += 1
            if form.cleaned_data["remove_logo"]:
                current.logo = ""
            current.save()
            ManagementEntry.objects.create(
                actor=user, organization=current, action="Ente aggiornato"
            )
            if old_logo and old_logo != current.logo.name:
                transaction.on_commit(partial(delete_cover, current.logo.storage, old_logo))
        return current
    except Exception:
        if old_logo is not None and current.logo and current.logo._committed:
            if current.logo.name != old_logo:
                delete_cover(current.logo.storage, current.logo.name)
        raise
