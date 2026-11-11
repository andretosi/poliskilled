from django.db.models import Q


def is_reviewer(user):
    return user.is_authenticated and user.has_perm("hub.review_activity")


def owned_activities(user):
    from .models import Activity

    return Activity.objects.filter(Q(creator=user) | Q(organizations__members=user)).distinct()


def can_edit(user, activity):
    return user.is_authenticated and (
        activity.creator_id == user.pk or activity.organizations.filter(members=user).exists()
    )


def can_review(user, activity):
    return is_reviewer(user) and not can_edit(user, activity)


def can_read(user, activity):
    return activity.status == "published" or can_edit(user, activity) or is_reviewer(user)
