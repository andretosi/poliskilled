"""Import reviewed public facts without claiming organizations or overwriting local edits."""

import json
from datetime import UTC, date, datetime
from hashlib import sha256
from unicodedata import normalize

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_aware

from .models import Activity, Organization, ReviewEntry
from .skill_graph import validate_predecessors

FIELDS = (
    "title",
    "description",
    "kind",
    "program",
    "icon",
    "source_url",
    "starts_at",
    "ends_on",
    "enrollment_deadline",
    "period",
    "location",
    "official_requirements",
    "availability",
    "preparation_notes",
    "source_checked_on",
    "level",
    "is_sample",
    "status",
    "technology",
    "community",
)


def signature(activity):
    values = {}
    for key in FIELDS:
        value = getattr(activity, key)
        if isinstance(value, datetime):
            value = value.astimezone(UTC)
        values[key] = str(value)
    values["organizations"] = sorted(activity.organizations.values_list("pk", flat=True))
    values["predecessors"] = sorted(activity.predecessors.values_list("pk", flat=True))
    return sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def timestamp(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None or not is_aware(parsed):
        raise ValidationError("Le date del catalogo devono includere il fuso orario.")
    return parsed


def defaults(item, checked):
    values = {
        key: item.get(key, "")
        for key in (
            "title",
            "description",
            "kind",
            "program",
            "icon",
            "source_url",
            "period",
            "location",
            "official_requirements",
            "preparation_notes",
        )
    }
    values.update(
        starts_at=timestamp(item.get("starts_at")),
        ends_on=date.fromisoformat(item["ends_on"]) if item.get("ends_on") else None,
        enrollment_deadline=timestamp(item.get("enrollment_deadline")),
        source_checked_on=checked,
        availability=item.get("availability", "unknown"),
        level=0,
        is_sample=False,
        status="published",
        technology=item.get("technology", True),
        community=item.get("community", False),
    )
    if not values["source_url"]:
        raise ValidationError("Ogni attività deve avere una fonte.")
    return values


@transaction.atomic
def import_catalog(data, archive_demo=False):
    checked = date.fromisoformat(data["reviewed_on"])
    items = data["activities"]
    keys = [item["key"] for item in items]
    if len(keys) != len(set(keys)):
        raise ValidationError("Chiavi attività duplicate nel catalogo.")
    editor, created = User.objects.get_or_create(
        username="poliskilled-catalog", defaults={"is_active": False}
    )
    if created:
        editor.set_unusable_password()
        editor.save(update_fields=["password"])
    if editor.is_active or editor.has_usable_password():
        raise ValidationError("Il nome riservato al catalogo appartiene a un account attivo.")
    organizations = {}
    for item in data["organizations"]:
        if item["key"] in organizations:
            raise ValidationError("Chiavi ente duplicate nel catalogo.")
        catalog_key = "catalog:" + sha256(item["key"].encode()).hexdigest()[:32]
        org = Organization.objects.filter(catalog_key=catalog_key).first()
        if org is None:
            org, _ = Organization.objects.get_or_create(
                normalized_name=normalize("NFKC", item["name"]).casefold(),
                defaults={
                    "name": item["name"],
                    "short_name": item.get("short_name", ""),
                    "description": item.get("description", ""),
                    "website": item.get("website", ""),
                    "catalog_source_url": item["source_url"],
                },
            )
            if org.catalog_key and org.catalog_key != catalog_key:
                raise ValidationError("Due chiavi del catalogo indicano lo stesso ente.")
            org.catalog_key = catalog_key
            org.save(update_fields=["catalog_key"])
        org.full_clean()
        # Existing profiles and their membership/verification are never replaced.
        organizations[item["key"]] = org
    activities, writable, old_signatures, old_parents = {}, set(), {}, {}
    result = {"created": 0, "updated": 0, "preserved": 0, "archived": 0}
    for item in items:
        key = "catalog:" + sha256(item["key"].encode()).hexdigest()[:32]
        values = defaults(item, checked)
        activity, created = Activity.objects.get_or_create(
            seed_key=key, defaults={**values, "creator": editor}
        )
        activities[item["key"]] = activity
        previous = activity.entries.last()
        current = signature(activity)
        if not created and (
            activity.creator_id != editor.pk
            or not previous
            or previous.snapshot.get("catalog_signature") != current
        ):
            result["preserved"] += 1
            continue
        writable.add(item["key"])
        old_signatures[item["key"]] = None if created else current
        old_parents[item["key"]] = set(activity.predecessors.values_list("pk", flat=True))
        for field, value in values.items():
            setattr(activity, field, value)
        activity.full_clean()
        activity.save(update_fields=FIELDS)
        try:
            orgs = [organizations[key] for key in item["organization_keys"]]
        except KeyError as error:
            raise ValidationError("Ente non trovato nel catalogo.") from error
        if not orgs:
            raise ValidationError("Ogni attività deve avere almeno un ente.")
        activity.organizations.set(orgs)
        result["created"] += int(created)
    # Replace this batch's edges together. Old edges must not reject a valid
    # new direction; cycles against unchanged/local edges still fail atomically.
    for key in writable:
        activities[key].predecessors.clear()
    for item in items:
        if item["key"] not in writable:
            continue
        activity = activities[item["key"]]
        try:
            parents = [activities[key] for key in item.get("predecessor_keys", [])]
        except KeyError as error:
            raise ValidationError("Tappa precedente non trovata nel catalogo.") from error
        retained = {
            parent.pk
            for parent in parents
            if parent.status != "published" and parent.pk in old_parents[item["key"]]
        }
        parent_ids = {parent.pk for parent in parents}
        validate_predecessors(activity.pk, parent_ids - retained, retained)
        activity.predecessors.set(parent_ids)
    for key in keys:
        if key not in writable:
            continue
        activity = activities[key]
        current = signature(activity)
        if current == old_signatures[key]:
            continue
        result["updated"] += int(old_signatures[key] is not None)
        activity.revision += 1
        activity.save(update_fields=["revision", "updated_at"])
        ReviewEntry.objects.create(
            activity=activity,
            author=editor,
            action="Catalogo verificato",
            revision=activity.revision,
            body="Scheda da fonti pubbliche; collegamenti editoriali di PoliSkilled.",
            snapshot={"catalog_signature": current, "source_url": activity.source_url},
        )
    if archive_demo:
        demos = Activity.objects.filter(seed_key__startswith="demo-activity-", status="published")
        for activity in demos:
            activity.status = "draft"
            activity.revision += 1
            activity.save(update_fields=["status", "revision", "updated_at"])
            ReviewEntry.objects.create(
                activity=activity,
                author=editor,
                action="Esempio archiviato",
                revision=activity.revision,
                body="Sostituito dal catalogo reale. I progressi originali sono conservati.",
            )
            result["archived"] += 1
    return result
