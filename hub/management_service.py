from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from .models import ManagementEntry, Organization
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


@transaction.atomic
def link_organization_member(actor, organization_id, username, revision):
    organization = Organization.objects.select_for_update().get(pk=organization_id)
    fresh_actor = User.objects.get(pk=actor.pk)
    if not is_reviewer(fresh_actor):
        raise PermissionDenied
    if str(organization.revision) != revision:
        raise ValidationError("L’ente è cambiato. Ricarica la pagina.")
    if not username or len(username) > 150:
        raise ValidationError("Inserisci un nome utente valido.")
    target = User.objects.filter(username=username, is_active=True).first()
    if target is None:
        raise ValidationError("Non trovo un account attivo con questo nome utente.")
    if target.pk == actor.pk:
        raise ValidationError("Per collegare il tuo account deve intervenire un altro gestore.")
    if organization.members.filter(pk=target.pk).exists():
        return
    organization.members.add(target)
    organization.revision += 1
    organization.save(update_fields=["revision"])
    ManagementEntry.objects.create(
        actor=fresh_actor, subject=target, organization=organization, action="Referente collegato"
    )
