import uuid
from unicodedata import normalize

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse

https_url = URLValidator(schemes=["https"])


def cover_path(instance, filename):
    return f"covers/{uuid.uuid4().hex}.jpg"


def logo_path(instance, filename):
    return f"logos/{uuid.uuid4().hex}.png"


class Organization(models.Model):
    name = models.CharField("nome", max_length=120, unique=True)
    normalized_name = models.CharField(max_length=360, unique=True, editable=False)
    short_name = models.CharField("sigla", max_length=24, blank=True)
    description = models.TextField("descrizione", blank=True)
    website = models.URLField("sito ufficiale", blank=True, validators=[https_url])
    verified = models.BooleanField("verificato", default=False)
    logo = models.ImageField("logo", upload_to=logo_path, blank=True)
    review_reason = models.TextField("motivazione", blank=True, max_length=1500)
    revision = models.PositiveIntegerField("versione", default=0)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="organizations")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="organization_name_case_insensitive")
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.normalized_name = normalize("NFKC", self.name).casefold()
        fields = kwargs.get("update_fields")
        if fields and "name" in fields:
            kwargs["update_fields"] = set(fields) | {"normalized_name"}
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        key = normalize("NFKC", self.name).casefold()
        if Organization.objects.filter(normalized_name=key).exclude(pk=self.pk).exists():
            raise ValidationError({"name": "Un ente con questo nome esiste già."})


class Activity(models.Model):
    seed_key = models.CharField(max_length=40, unique=True, null=True, editable=False)

    class Kind(models.TextChoices):
        EVENT = "event", "Evento"
        COURSE = "course", "Corso"
        PROJECT = "project", "Progetto"

    class Status(models.TextChoices):
        DRAFT = "draft", "Bozza"
        PENDING = "pending", "In revisione"
        CHANGES = "changes", "Da rivedere"
        PUBLISHED = "published", "Pubblicata"

    title = models.CharField("titolo", max_length=120)
    description = models.TextField("descrizione", max_length=5000)
    kind = models.CharField("tipo", max_length=12, choices=Kind, default=Kind.EVENT)
    program = models.CharField(
        "programma",
        max_length=20,
        blank=True,
        choices=[("", "Nessuno"), ("passion", "Passion in Action")],
    )
    level = models.PositiveSmallIntegerField(
        "livello",
        default=1,
        choices=[(1, "Esplora"), (2, "Approfondisci"), (3, "Mettiti alla prova")],
    )
    tracks = models.ManyToManyField(
        "Track", through="TrackStep", related_name="activities", blank=True, verbose_name="percorsi"
    )
    predecessors = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="successors",
        blank=True,
        verbose_name="tappe precedenti",
    )
    icon = models.CharField(
        "icona",
        max_length=16,
        blank=True,
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
    )
    technology = models.BooleanField("Tecnologia", default=True)
    community = models.BooleanField("Persone", default=False)
    organizations = models.ManyToManyField(Organization, related_name="activities")
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    image = models.ImageField("immagine", upload_to=cover_path, blank=True)
    source_url = models.URLField("link di riferimento", blank=True, validators=[https_url])
    starts_at = models.DateTimeField("data e ora", null=True, blank=True)
    location = models.CharField("dove", max_length=120, blank=True)
    is_sample = models.BooleanField("esempio dimostrativo", default=False)
    status = models.CharField(max_length=12, choices=Status, default=Status.DRAFT)
    revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]
        permissions = [("review_activity", "Can review proposals and verify organizations")]
        indexes = [models.Index(fields=["status", "kind"])]

    def __str__(self):
        return self.title

    @property
    def icon_name(self):
        return self.icon or {"project": "flag", "event": "people", "course": "circuit"}[self.kind]

    def get_absolute_url(self):
        return reverse("activity", args=[self.pk])


class ReviewEntry(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="entries")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=32)
    body = models.TextField(max_length=3000, blank=True)
    revision = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]


class Track(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=800)
    eyebrow = models.CharField(max_length=60, default="Dalla curiosità al progetto")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return self.title

    @property
    def color_index(self):
        return (self.pk - 1) % 6


class TrackStep(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="steps")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    note = models.CharField(max_length=180, blank=True)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["track", "activity"], name="unique_track_activity")
        ]


class AuthThrottle(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    window = models.PositiveBigIntegerField()
    count = models.PositiveIntegerField(default=0)


class ActivityProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "activity"], name="unique_user_activity_progress"
            )
        ]


class ProgressRevision(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    revision = models.PositiveBigIntegerField(default=0)


class ManagementEntry(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="autore"
    )
    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="management_entries",
        verbose_name="account interessato",
    )
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="management_entries",
        verbose_name="ente",
    )
    action = models.CharField("azione", max_length=32)
    reason = models.TextField("motivazione", blank=True, max_length=1500)
    created_at = models.DateTimeField("data", auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "operazione di gestione"
        verbose_name_plural = "operazioni di gestione"
