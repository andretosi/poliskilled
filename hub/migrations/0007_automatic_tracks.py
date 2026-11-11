from collections import defaultdict, deque

from django.db import migrations, models


def convert_steps(apps, schema_editor):
    Activity = apps.get_model("hub", "Activity")
    Step = apps.get_model("hub", "TrackStep")
    tracks = defaultdict(lambda: defaultdict(list))
    for step in Step.objects.all():
        tracks[step.track_id][step.stage].append(step.activity_id)
    edges = set()
    for stages in tracks.values():
        levels = sorted(stages)
        for before, after in zip(levels, levels[1:]):
            edges.update((child, parent) for child in stages[after] for parent in stages[before])
    parents = defaultdict(set)
    for child, parent in edges:
        parents[child].add(parent)
    # Old manual levels can conflict between tracks; do not publish a cyclic graph.
    nodes = {node for edge in edges for node in edge}
    remaining = {node: len(parents[node]) for node in nodes}
    children = defaultdict(set)
    for child, parent in edges:
        children[parent].add(child)
    ready = deque(node for node in nodes if not remaining[node])
    visited = 0
    while ready:
        node = ready.popleft()
        visited += 1
        for child in children[node]:
            remaining[child] -= 1
            if not remaining[child]:
                ready.append(child)
    if visited != len(nodes):
        raise RuntimeError(
            "I percorsi esistenti contengono un ciclo. Correggere le tappe prima di migrare."
        )
    relation = Activity.predecessors.through
    relation.objects.bulk_create(
        [relation(from_activity_id=child, to_activity_id=parent) for child, parent in sorted(edges)]
    )
    Activity.objects.filter(seed_key="demo-activity-7", revision=1, kind="event").update(
        kind="course"
    )
    for index, icon in enumerate(
        ["circuit", "code", "robot", "signal", "flag", "robot", "flag", "design", "people"]
    ):
        Activity.objects.filter(seed_key=f"demo-activity-{index}").update(icon=icon)


class Migration(migrations.Migration):
    dependencies = [("hub", "0006_progress_revision")]
    operations = [
        migrations.AddField(
            model_name="activity",
            name="tracks",
            field=models.ManyToManyField(
                blank=True,
                related_name="activities",
                through="hub.TrackStep",
                to="hub.track",
                verbose_name="percorsi",
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="predecessors",
            field=models.ManyToManyField(
                blank=True,
                related_name="successors",
                symmetrical=False,
                to="hub.activity",
                verbose_name="tappe precedenti",
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="icon",
            field=models.CharField(
                "icona",
                blank=True,
                max_length=16,
                choices=[
                    ("", "Automatica"),
                    ("circuit", "Elettronica"),
                    ("code", "Codice"),
                    ("signal", "Segnali"),
                    ("robot", "Robotica"),
                    ("people", "Community"),
                    ("design", "Prototipi"),
                    ("flag", "Progetto"),
                ],
            ),
        ),
        migrations.RunPython(convert_steps),
        migrations.RemoveField(model_name="trackstep", name="stage"),
        migrations.RemoveField(model_name="trackstep", name="order"),
        migrations.AlterModelOptions(name="trackstep", options={"ordering": ["pk"]}),
    ]
