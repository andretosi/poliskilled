from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hub.models import Activity, Organization, ReviewEntry, Track, TrackStep
from hub.sample_data import ACTIVITIES, ACTIVITY_ICONS, ORGANIZATIONS, PREDECESSORS, TRACKS


class Command(BaseCommand):
    help = "Create local sample data and passwordless demo identities; never overwrites edits."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.DEMO_MODE:
            raise CommandError("Demo seeding requires DJANGO_DEBUG=1 and POLISKILLED_DEMO=1.")
        users = {}
        for role in ["aea", "moderatore", "studente"]:
            user, created = User.objects.get_or_create(username=f"demo-{role}")
            if created:
                user.set_unusable_password()
                user.save()
            if user.has_usable_password():
                raise CommandError("A real account already uses a reserved demo name.")
            users[role] = user
        users["moderatore"].user_permissions.add(
            Permission.objects.get(codename="review_activity", content_type__app_label="hub")
        )
        organizations = {}
        for short, name, url, description in ORGANIZATIONS:
            organizations[short], _ = Organization.objects.get_or_create(
                name=name,
                defaults={
                    "short_name": short,
                    "website": url,
                    "description": description,
                    "verified": True,
                },
            )
        organizations["AEA"].members.add(users["aea"])
        activities = []
        created_indices = set()
        # Seed IDs are positional and immutable: append new sample records, never reorder.
        for index, (title, kind, level, orgs, sample, url, description) in enumerate(ACTIVITIES):
            activity, created = Activity.objects.get_or_create(
                seed_key=f"demo-activity-{index}",
                defaults={
                    "title": title,
                    "creator": users["aea"],
                    "kind": kind,
                    "icon": ACTIVITY_ICONS.get(index, ""),
                    "program": "passion" if index == 7 else "",
                    "level": level,
                    "is_sample": sample,
                    "source_url": url,
                    "description": description,
                    "status": "published",
                    "revision": 1,
                    "community": kind == "event",
                    "technology": True,
                },
            )
            if created:
                created_indices.add(index)
                activity.organizations.set([organizations[name] for name in orgs])
                ReviewEntry.objects.create(
                    activity=activity,
                    author=users["moderatore"],
                    action="Esempio iniziale",
                    revision=1,
                    body="Dato importato per la dimostrazione locale.",
                )
            activities.append(activity)
        for order, (slug, title, description, indices) in enumerate(TRACKS):
            track, created = Track.objects.get_or_create(
                slug=slug, defaults={"title": title, "description": description, "order": order}
            )
            if created:
                for index in indices:
                    TrackStep.objects.create(track=track, activity=activities[index])
        for index in created_indices:
            activities[index].predecessors.set(
                [activities[parent] for parent in PREDECESSORS.get(index, [])]
            )
        self.stdout.write(self.style.SUCCESS("Demo pronta: 4 enti, 9 attività, 2 percorsi."))
