from io import BytesIO
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from .base import HubTestCase


class StorageTests(HubTestCase):
    def setUp(self):
        content = BytesIO()
        Image.new("RGB", (40, 40), "green").save(content, format="JPEG")
        self.content = content.getvalue()
        self.activity.image.save("old.jpg", ContentFile(self.content))
        self.old_name = self.activity.image.name
        self.storage = self.activity.image.storage
        self.client.force_login(self.owner)

    def replacement(self):
        return SimpleUploadedFile("new.jpg", self.content, "image/jpeg")

    def test_replaced_cover_deleted_only_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(
                reverse("edit_proposal", args=[self.activity.pk]),
                self.payload(image=self.replacement()),
            )
            self.assertEqual(response.status_code, 302)
            self.assertTrue(self.storage.exists(self.old_name))
        self.assertEqual(len(callbacks), 1)
        self.assertFalse(self.storage.exists(self.old_name))
        self.activity.refresh_from_db()
        self.assertTrue(self.storage.exists(self.activity.image.name))

    def test_rollback_deletes_new_upload_and_preserves_original(self):
        before = set(self.storage.listdir("covers")[1])
        with patch("hub.proposal_service.ReviewEntry.objects.create", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse("edit_proposal", args=[self.activity.pk]),
                    self.payload(image=self.replacement()),
                )
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.image.name, self.old_name)
        self.assertTrue(self.storage.exists(self.old_name))
        self.assertEqual(set(self.storage.listdir("covers")[1]), before)

    def test_edit_does_not_expose_stored_image(self):
        response = self.client.get(reverse("edit_proposal", args=[self.activity.pk]))
        self.assertNotContains(response, reverse("cover", args=[self.activity.pk]))
        self.assertNotContains(response, self.activity.image.url)
