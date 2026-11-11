from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings

from hub.models import Activity, Organization
from hub.skill_graph import graph_baseline


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class HubTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner")
        cls.other = User.objects.create_user("other")
        cls.reviewer = User.objects.create_user("reviewer")
        cls.reviewer.user_permissions.add(
            Permission.objects.get(codename="review_activity", content_type__app_label="hub")
        )
        cls.org = Organization.objects.create(name="Verified", verified=True)
        cls.org.members.add(cls.owner)
        cls.partner = Organization.objects.create(name="Partner", verified=True)
        cls.partner.members.add(cls.other)
        cls.activity = Activity.objects.create(
            title="Test robotics",
            description="Build together.",
            kind="project",
            creator=cls.owner,
            status="pending",
            revision=1,
        )
        cls.activity.organizations.add(cls.org)

    def payload(self, **overrides):
        return {
            "title": "Test robotics",
            "description": "Updated description",
            "kind": "project",
            "level": 2,
            "organizations": [self.org.pk],
            "technology": "on",
            "revision": self.activity.revision,
            "graph_baseline": graph_baseline(self.activity),
            "intent": "submit",
            **overrides,
        }
