from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from .models import ManagementEntry
from .permissions import is_reviewer


def managers():
    return User.objects.filter(
        Q(is_superuser=True)
        | Q(
            user_permissions__codename="review_activity",
            user_permissions__content_type__app_label="hub",
        )
        | Q(
            groups__permissions__codename="review_activity",
            groups__permissions__content_type__app_label="hub",
        )
    ).distinct()


@transaction.atomic
def set_manager(actor, target_id, enabled, expected):
    # A shared row serializes role changes; re-read authority after acquiring it.
    permission = Permission.objects.select_for_update().get(
        codename="review_activity", content_type__app_label="hub"
    )
    fresh_actor = User.objects.get(pk=actor.pk)
    if not is_reviewer(fresh_actor):
        raise PermissionDenied
    target = User.objects.select_for_update().get(pk=target_id)
    if target.pk == actor.pk or target.is_superuser or not target.is_active:
        raise ValidationError("Non puoi cambiare questo ruolo da qui.")
    current = is_reviewer(target)
    if current != expected:
        raise ValidationError("Il ruolo è già cambiato. Ricarica la pagina.")
    if target.groups.filter(permissions=permission).exists():
        raise ValidationError("Questo ruolo proviene da un gruppo: serve il responsabile tecnico.")
    if enabled == current:
        return
    if enabled:
        target.user_permissions.add(permission)
    else:
        target.user_permissions.remove(permission)
    ManagementEntry.objects.create(
        actor=fresh_actor,
        subject=target,
        action="Gestore aggiunto" if enabled else "Gestore rimosso",
    )
