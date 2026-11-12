from django import template
from django.urls import reverse

from hub.models import Activity
from insights.audience import public_activities
from insights.models import ActivityInterest

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
        "label": "Salva obiettivo",
        "selected_label": "Obiettivo salvato ✓",
        "active": activity.pk in request._intent_ids["interested"],
        "visible": activity.pk in request._intent_ids["public"],
    }


@register.inclusion_tag("insights/partials/saved_intents.html", takes_context=True)
def saved_intents(context):
    user = context["request"].user
    interests = Activity.objects.none()
    if user.is_authenticated:
        interests = public_activities().filter(activityinterest__user=user).order_by("title")
    return {
        "interested_activities": interests,
        "request": context["request"],
    }
