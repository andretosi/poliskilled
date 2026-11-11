from django import template
from django.urls import reverse

from hub.models import Activity, Track
from insights.audience import public_activities
from insights.models import ActivityInterest, TrackFollow

register = template.Library()


@register.inclusion_tag("insights/partials/intent_button.html", takes_context=True)
def interest_button(context, activity):
    request = context["request"]
    user = request.user
    if not hasattr(request, "_intent_ids"):
        request._intent_ids = {
            "public": set(public_activities().values_list("pk", flat=True)),
            "interested": set(
                ActivityInterest.objects.filter(user=user).values_list("activity_id", flat=True)
            )
            if user.is_authenticated
            else set(),
        }
    return {
        "kind": "interests",
        "pk": activity.pk,
        "url": reverse("insights:interest", args=[activity.pk]),
        "label": "Mi interessa",
        "selected_label": "Ti interessa ✓",
        "active": activity.pk in request._intent_ids["interested"],
        "visible": activity.pk in request._intent_ids["public"],
    }


@register.inclusion_tag("insights/partials/intent_button.html", takes_context=True)
def follow_button(context, track):
    user = context["request"].user
    return {
        "kind": "follows",
        "pk": track.pk,
        "url": reverse("insights:follow", args=[track.pk]),
        "label": "Segui percorso",
        "selected_label": "Segui già ✓",
        "active": user.is_authenticated
        and TrackFollow.objects.filter(user=user, track=track).exists(),
        "visible": True,
    }


@register.inclusion_tag("insights/partials/saved_intents.html", takes_context=True)
def saved_intents(context):
    user = context["request"].user
    interests, follows = Activity.objects.none(), Track.objects.none()
    if user.is_authenticated:
        interests = public_activities().filter(activityinterest__user=user).order_by("title")
        follows = Track.objects.filter(trackfollow__user=user).distinct()
    return {
        "interested_activities": interests,
        "followed_tracks": follows,
        "request": context["request"],
    }
