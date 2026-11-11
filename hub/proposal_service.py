from functools import partial

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.forms.models import construct_instance
from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare

from .models import Activity, Organization, ReviewEntry, Track
from .permissions import can_edit
from .skill_graph import graph_baseline, validate_predecessors
from .uploads import delete_cover


def save_proposal(form, user, intent, pk):
    """Validate outside the writer lock; recheck mutable authority and version inside it."""
    current = None
    old_image = None
    # Keep the validated choices: a filtered queryset rerun could silently drop revoked rows.
    org_ids = [org.pk for org in form.cleaned_data["organizations"]]
    predecessor_ids = [item.pk for item in form.cleaned_data["predecessors"]]
    track_ids = [track.pk for track in form.cleaned_data["tracks"]]
    try:
        with transaction.atomic():
            current = (
                get_object_or_404(Activity.objects.select_for_update(), pk=pk)
                if pk
                else Activity(creator=user)
            )
            if pk and not can_edit(user, current):
                raise PermissionDenied
            if form.cleaned_data["revision"] != current.revision:
                form.add_error(
                    None, "La proposta è cambiata. Ricarica la pagina prima di riprovare."
                )
                return None
            if pk and not constant_time_compare(
                form.cleaned_data.get("graph_baseline", ""), graph_baseline(current)
            ):
                form.add_error(None, "I collegamenti sono cambiati. Ricarica la proposta.")
                return None
            organizers = Organization.objects.filter(pk__in=org_ids, verified=True)
            if organizers.count() != len(org_ids) or not organizers.filter(members=user).exists():
                form.add_error(
                    "organizations", "Gli enti o i tuoi permessi sono cambiati. Ricarica."
                )
                return None
            if Track.objects.filter(pk__in=track_ids).count() != len(track_ids):
                form.add_error("tracks", "Un percorso non è più disponibile. Ricarica la proposta.")
                return None
            retained = (
                list(current.predecessors.exclude(status="published").values_list("pk", flat=True))
                if pk
                else []
            )
            try:
                validate_predecessors(
                    current.pk,
                    predecessor_ids,
                    retained,
                )
            except ValidationError as error:
                form.add_error("predecessors", error)
                return None
            old_image = current.image.name
            form.instance = construct_instance(form, current, form._meta.fields, form._meta.exclude)
            current = form.save(commit=False)
            current.revision += 1
            current.status = (
                Activity.Status.PENDING if intent == "submit" else Activity.Status.DRAFT
            )
            current.save()
            form.save_m2m()
            current.predecessors.add(*retained)
            ReviewEntry.objects.create(
                activity=current,
                author=user,
                revision=current.revision,
                action="Proposta inviata" if intent == "submit" else "Bozza salvata",
                snapshot={
                    "title": current.title,
                    "description": current.description,
                    "kind": current.get_kind_display(),
                    "program": current.get_program_display(),
                    "icon": current.get_icon_display(),
                    "tracks": list(current.tracks.values_list("title", flat=True)),
                    "predecessors": list(
                        current.predecessors.filter(status="published").values_list(
                            "title", flat=True
                        )
                    ),
                    "level": current.get_level_display(),
                    "organizations": list(current.organizations.values_list("name", flat=True)),
                    "source_url": current.source_url,
                    "location": current.location,
                    "starts_at": current.starts_at.isoformat() if current.starts_at else "",
                    "technology": current.technology,
                    "community": current.community,
                },
            )
            if old_image and old_image != current.image.name:
                transaction.on_commit(partial(delete_cover, current.image.storage, old_image))
        return current
    except Exception:
        if current and old_image is not None and current.image and current.image._committed:
            if current.image.name != old_image:
                delete_cover(current.image.storage, current.image.name)
        raise
