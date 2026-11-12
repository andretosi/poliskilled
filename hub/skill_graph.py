from collections import defaultdict, deque

from django.core.exceptions import ValidationError
from django.utils.crypto import salted_hmac

from .models import Activity


def graph_baseline(activity, visible=None):
    if not activity.pk:
        return ""
    if visible is None:
        visible = activity.predecessors.filter(status="published").values_list("pk", flat=True)
    visible = sorted(visible)
    return salted_hmac("graph-form", f"{activity.pk}:{activity.revision}:{visible}").hexdigest()


def validate_predecessors(activity_id, predecessor_ids, retained=()):
    """Validate the complete graph, including proposals hidden during moderation."""
    ids = set(predecessor_ids)
    if Activity.objects.filter(pk__in=ids, status="published").count() != len(ids):
        raise ValidationError("Una tappa precedente non è più pubblica. Ricarica la proposta.")
    if not activity_id:
        return
    parents = defaultdict(set)
    for child, parent in Activity.predecessors.through.objects.values_list(
        "from_activity_id", "to_activity_id"
    ):
        parents[child].add(parent)
    pending = list(ids | set(retained))
    visited = set()
    while pending:
        node = pending.pop()
        if node == activity_id:
            raise ValidationError(
                "Questo collegamento crea un ciclo. Scegli una tappa precedente diversa."
            )
        if node not in visited:
            visited.add(node)
            pending.extend(parents[node])


def load_public_graph():
    """Load once per request when several objectives share the same graph."""
    public = {
        activity.pk: activity
        for activity in Activity.objects.filter(status="published").order_by("title", "pk")
    }
    parents = defaultdict(set)
    for child, parent in Activity.predecessors.through.objects.values_list(
        "from_activity_id", "to_activity_id"
    ):
        if child in public and parent in public:
            parents[child].add(parent)
    return public, parents


def build_track(track, graph=None):
    """Select public members + ancestors, then assign levels by longest dependency path."""
    steps = {step.activity_id: step for step in track.steps.all()}
    return _build(set(steps), graph, legacy_steps=steps)


def build_goal(activity, graph=None):
    """An activity is the destination; include only its published ancestors."""
    return _build({activity.pk}, graph, goal_id=activity.pk)


def _build(selected, graph=None, goal_id=None, legacy_steps=None):
    public, parents = graph if graph is not None else load_public_graph()
    steps = legacy_steps or {}
    included = selected & public.keys()
    pending = list(included)
    while pending:
        for parent in parents[pending.pop()]:
            if parent not in included:
                included.add(parent)
                pending.append(parent)
    children = defaultdict(set)
    remaining = {}
    for child in included:
        remaining[child] = len(parents[child])
        for parent in parents[child]:
            children[parent].add(child)
    ready = deque(sorted(pk for pk in included if not remaining[pk]))
    rank = {pk: 1 for pk in ready}
    visited = 0
    while ready:
        parent = ready.popleft()
        visited += 1
        for child in sorted(children[parent]):
            rank[child] = max(rank.get(child, 1), rank[parent] + 1)
            remaining[child] -= 1
            if not remaining[child]:
                ready.append(child)
    if visited != len(included):
        raise ValidationError("Il percorso contiene collegamenti circolari da correggere.")
    levels = defaultdict(list)
    for pk, activity in public.items():
        if pk not in included:
            continue
        step = steps.get(pk)
        levels[rank[pk]].append(
            {
                "activity": activity,
                "legacy_step": step.pk if step else "",
                "note": step.note if step else "",
                "parents": sorted(parents[pk]),
                "goal": pk == goal_id if goal_id else activity.kind == "project",
            }
        )
    # Order each row toward its already placed children to reduce crossings.
    positions = {}
    for number in sorted(levels, reverse=True):

        def target_position(step):
            destinations = [
                positions[pk] for pk in children[step["activity"].pk] if pk in positions
            ]
            return sum(destinations) / len(destinations) if destinations else 0

        levels[number].sort(key=target_position)
        count = len(levels[number])
        for index, step in enumerate(levels[number]):
            positions[step["activity"].pk] = (index + 1) / (count + 1)
    return [
        {"number": number, "label": "Parti da qui" if number == 1 else "Prosegui", "steps": nodes}
        for number, nodes in sorted(levels.items())
    ]
