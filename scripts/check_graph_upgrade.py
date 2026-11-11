"""Exercise the historical graph migration on a disposable SQLite database."""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def check(scenario):
    with TemporaryDirectory(prefix="poliskilled-graph-migration-") as directory:
        os.environ.update(
            DJANGO_DEBUG="1",
            DJANGO_SETTINGS_MODULE="poliskilled.settings",
            DJANGO_DB_PATH=str(Path(directory) / "upgrade.sqlite3"),
        )
        import django

        django.setup()
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.db.migrations.recorder import MigrationRecorder

        before = [("hub", "0006_progress_revision")]
        after = [("hub", "0007_automatic_tracks")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        apps = executor.loader.project_state(before).apps
        User, Activity, Track, Step, Progress, Revision = [
            apps.get_model(app, name)
            for app, name in [
                ("auth", "User"),
                ("hub", "Activity"),
                ("hub", "Track"),
                ("hub", "TrackStep"),
                ("hub", "ActivityProgress"),
                ("hub", "ProgressRevision"),
            ]
        ]
        user = User.objects.create(username="migration-test", password="!")
        first = Activity.objects.create(title="Base", creator=user, status="published")
        second = Activity.objects.create(title="Bridge", creator=user, status="published")
        end = Activity.objects.create(
            title="Edited project",
            seed_key="demo-activity-7",
            creator=user,
            kind="project",
            revision=2,
            status="published",
        )
        one = Track.objects.create(slug="one", title="One")
        two = Track.objects.create(slug="two", title="Two")
        for track, items in [
            (one, [first, second, end]),
            (two, [second, first] if scenario == "cycle" else [second, end]),
        ]:
            for stage, activity in enumerate(items, 1):
                Step.objects.create(
                    track=track,
                    activity=activity,
                    stage=stage,
                    order=stage,
                    note=f"Keep {activity.pk}",
                )
        old_steps = list(Step.objects.order_by("pk").values_list("pk", "activity_id", "note"))
        progress = Progress.objects.create(user=user, activity=first)
        Revision.objects.create(user=user, revision=5)
        executor = MigrationExecutor(connection)
        if scenario == "cycle":
            try:
                executor.migrate(after)
            except RuntimeError as error:
                assert "ciclo" in str(error)
            else:
                raise AssertionError("A contradictory legacy graph was accepted")
            assert after[0] not in MigrationRecorder(connection).applied_migrations()
            assert "hub_activity_predecessors" not in connection.introspection.table_names()
            assert (
                list(Step.objects.order_by("pk").values_list("pk", "activity_id", "note"))
                == old_steps
            )
        else:
            executor.migrate(after)
            updated = executor.loader.project_state(after).apps
            NewActivity = updated.get_model("hub", "Activity")
            NewStep = updated.get_model("hub", "TrackStep")
            assert (
                list(NewStep.objects.order_by("pk").values_list("pk", "activity_id", "note"))
                == old_steps
            )
            assert set(
                NewActivity.predecessors.through.objects.values_list(
                    "from_activity_id", "to_activity_id"
                )
            ) == {(second.pk, first.pk), (end.pk, second.pk)}
            assert NewActivity.objects.get(pk=end.pk).kind == "project"
            assert (
                updated.get_model("hub", "ActivityProgress").objects.get(pk=progress.pk).activity_id
                == first.pk
            )
            assert (
                updated.get_model("hub", "ProgressRevision").objects.get(user_id=user.pk).revision
                == 5
            )
        connection.close()
        print(f"Historical graph migration: {scenario} passed")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"valid", "cycle"}:
        raise SystemExit("Expected valid or cycle")
    check(sys.argv[1])
