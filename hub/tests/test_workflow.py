from django.contrib.auth.models import Permission
from django.urls import reverse

from hub.models import Activity, ReviewEntry

from .base import HubTestCase


class WorkflowTests(HubTestCase):
    def decision(self, decision="approve", reason="", revision=1):
        return self.client.post(
            reverse("decide", args=[self.activity.pk]),
            {
                "decision": decision,
                "reason": reason,
                "revision": revision,
            },
        )

    def test_full_changes_resubmit_approve_thread(self):
        self.client.force_login(self.reviewer)
        self.decision("changes", "Add the location.")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, "changes")
        self.client.force_login(self.owner)
        self.client.post(reverse("comment", args=[self.activity.pk]), {"body": "I will add it."})
        self.client.post(
            reverse("edit_proposal", args=[self.activity.pk]), self.payload(location="Campus")
        )
        self.activity.refresh_from_db()
        self.assertEqual((self.activity.status, self.activity.revision), ("pending", 2))
        self.client.force_login(self.reviewer)
        self.decision(revision=2)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, "published")
        self.assertEqual(self.activity.entries.count(), 4)
        entry = self.activity.entries.get(action="Proposta inviata")
        self.assertEqual(entry.snapshot["location"], "Campus")
        self.client.logout()
        self.assertContains(self.client.get(self.activity.get_absolute_url()), "Test robotics")
        self.assertNotContains(
            self.client.get(self.activity.get_absolute_url()), "Add the location."
        )

    def test_rejection_requires_reason(self):
        self.client.force_login(self.reviewer)
        self.decision("changes", "   ")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, "pending")
        self.assertEqual(self.activity.entries.count(), 0)

    def test_self_approval_blocked_even_with_permission(self):
        self.owner.user_permissions.add(
            Permission.objects.get(codename="review_activity", content_type__app_label="hub")
        )
        self.client.force_login(self.owner)
        self.assertEqual(self.decision().status_code, 403)

    def test_coorganizer_can_edit_but_not_review(self):
        self.activity.organizations.add(self.partner)
        self.other.user_permissions.add(
            Permission.objects.get(codename="review_activity", content_type__app_label="hub")
        )
        self.client.force_login(self.other)
        self.assertEqual(self.decision().status_code, 403)
        response = self.client.post(
            reverse("edit_proposal", args=[self.activity.pk]),
            self.payload(organizations=[self.org.pk, self.partner.pk]),
        )
        self.assertEqual(response.status_code, 302)

    def test_stale_review_cannot_publish_new_version(self):
        self.client.force_login(self.reviewer)
        self.decision(revision=0)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, "pending")

    def test_duplicate_decision_has_one_entry(self):
        self.client.force_login(self.reviewer)
        self.decision()
        self.decision()
        self.assertEqual(self.activity.entries.count(), 1)

    def test_stale_edit_cannot_overwrite(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("edit_proposal", args=[self.activity.pk]),
            self.payload(revision=0, title="Stale"),
        )
        self.assertContains(response, "La proposta è cambiata")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.title, "Test robotics")

    def test_edit_published_withdraws_until_review(self):
        Activity.objects.filter(pk=self.activity.pk).update(status="published")
        self.client.force_login(self.owner)
        self.client.post(reverse("edit_proposal", args=[self.activity.pk]), self.payload())
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, "pending")
        self.client.logout()
        self.assertEqual(self.client.get(self.activity.get_absolute_url()).status_code, 404)

    def test_save_draft_and_submit(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("propose"), self.payload(revision=0, intent="draft"))
        self.assertEqual(response.status_code, 302)
        item = Activity.objects.exclude(pk=self.activity.pk).get()
        self.assertEqual(item.status, "draft")
        self.assertEqual(item.revision, 1)

    def test_partner_cannot_be_sole_organizer(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("propose"), self.payload(organizations=[self.partner.pk], revision=0)
        )
        self.assertContains(response, "Seleziona almeno un ente verificato")
        self.assertEqual(Activity.objects.count(), 1)

    def test_revoked_org_cannot_be_published(self):
        self.org.verified = False
        self.org.save()
        self.client.force_login(self.reviewer)
        self.decision()
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, "pending")

    def test_private_comment_does_not_leak(self):
        ReviewEntry.objects.create(
            activity=self.activity,
            author=self.owner,
            revision=1,
            action="Commento",
            body="PRIVATE_THREAD_MARKER",
        )
        Activity.objects.filter(pk=self.activity.pk).update(status="published")
        self.client.force_login(self.other)
        response = self.client.get(self.activity.get_absolute_url())
        self.assertNotContains(response, "PRIVATE_THREAD_MARKER")
        self.assertEqual(
            self.client.post(
                reverse("comment", args=[self.activity.pk]), {"body": "Intrusion"}
            ).status_code,
            403,
        )
