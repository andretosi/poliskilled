import warnings
from io import BytesIO
from unicodedata import normalize

from django import forms
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.utils.crypto import constant_time_compare
from PIL import Image, ImageOps

from accounts.forms import EmailRegistrationForm

from .models import Activity, Organization
from .skill_graph import graph_baseline, validate_predecessors
from .widgets import PrivateImageInput


class ActivityForm(forms.ModelForm):
    revision = forms.IntegerField(widget=forms.HiddenInput, initial=0)
    graph_baseline = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Activity
        fields = [
            "title",
            "kind",
            "description",
            "organizations",
            "technology",
            "community",
            "level",
            "program",
            "icon",
            "predecessors",
            "preparation_notes",
            "image",
            "source_url",
            "starts_at",
            "period",
            "ends_on",
            "enrollment_deadline",
            "availability",
            "official_requirements",
            "location",
        ]
        widgets = {
            "image": PrivateImageInput,
            "description": forms.Textarea(attrs={"rows": 5}),
            "preparation_notes": forms.Textarea(attrs={"rows": 2}),
            "official_requirements": forms.Textarea(attrs={"rows": 2}),
            "organizations": forms.CheckboxSelectMultiple,
            "predecessors": forms.CheckboxSelectMultiple,
            "icon": forms.RadioSelect,
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "ends_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "enrollment_deadline": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }
        labels = {
            "title": "Titolo",
            "kind": "Tipo",
            "description": "Descrizione",
            "organizations": "Enti organizzatori",
            "predecessors": "Preparazione consigliata",
        }
        help_texts = {
            "organizations": (
                "Seleziona almeno un tuo ente. I co-organizzatori saranno verificati in revisione."
            ),
            "image": "JPG, PNG o WebP, massimo 3 MB.",
            "source_url": "Facoltativo. Pagina ufficiale o iscrizioni (https).",
            "level": "Un orientamento, non un requisito di ammissione.",
            "period": (
                "Se compilato, viene mostrato al posto della data e ora. "
                "Aggiornalo quando cambia il calendario."
            ),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["predecessors"].queryset = (
            Activity.objects.filter(status="published")
            .exclude(pk=self.instance.pk)
            .order_by("title")
        )
        # Freeze labels and selected IDs together: rendering must not rerun a
        # public-only queryset after the baseline has already been signed.
        available = list(self.fields["predecessors"].queryset)
        linked = {item.pk for item in self.initial.get("predecessors", [])}
        visible = [item.pk for item in available if item.pk in linked]
        self.fields["predecessors"].choices = [(item.pk, str(item)) for item in available]
        self.initial["predecessors"] = visible
        self.initial["graph_baseline"] = graph_baseline(self.instance, visible)
        self.fields["organizations"].queryset = Organization.objects.filter(verified=True)
        self.fields["revision"].initial = self.instance.revision
        self.fields["starts_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["enrollment_deadline"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["availability"].required = False
        if not self.instance.pk:
            self.initial["organizations"] = user.organizations.filter(verified=True)

    def clean(self):
        data = super().clean()
        if self.instance.pk and not constant_time_compare(
            data.get("graph_baseline", ""), graph_baseline(self.instance)
        ):
            self.add_error(
                None, "I collegamenti sono cambiati. Ricarica la proposta prima di salvare."
            )
        return data

    def clean_predecessors(self):
        predecessors = self.cleaned_data["predecessors"]
        validate_predecessors(self.instance.pk, list(predecessors.values_list("pk", flat=True)))
        return predecessors

    def clean_availability(self):
        return self.cleaned_data["availability"] or self.instance.availability

    def clean_organizations(self):
        organizations = self.cleaned_data["organizations"]
        if not organizations.filter(members=self.user, verified=True).exists():
            raise forms.ValidationError("Seleziona almeno un ente verificato di cui fai parte.")
        return organizations

    def clean_image(self):
        upload = self.cleaned_data.get("image")
        if not upload or not hasattr(upload, "content_type"):
            return upload
        if upload.size > 3 * 1024 * 1024:
            raise forms.ValidationError("L'immagine supera 3 MB.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                image = Image.open(upload)
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError
                if image.width * image.height > 12_000_000:
                    raise ValueError
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((1600, 1000))
                output = BytesIO()
                image.save(output, format="JPEG", quality=85)
        except (ValueError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError):
            raise forms.ValidationError(
                "Usa un JPG, PNG o WebP valido, fino a 12 megapixel."
            ) from None
        return ContentFile(output.getvalue(), name="cover.jpg")


class RegisterForm(EmailRegistrationForm):
    email = forms.EmailField(label="Email di contatto")
    organization = forms.CharField(label="Nome dell'ente", max_length=120)
    website = forms.URLField(label="Sito ufficiale (https)", required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "organization",
            "website",
            "password1",
            "password2",
            "updates_opt_in",
        )

    def clean_organization(self):
        name = self.cleaned_data["organization"].strip()
        if Organization.objects.filter(normalized_name=normalize("NFKC", name).casefold()).exists():
            raise forms.ValidationError(
                "Questo ente esiste già. Crea un account personale (o usa quello che hai), "
                "poi chiedi a un gestore di collegarti come referente."
            )
        return name

    def clean_website(self):
        website = self.cleaned_data["website"]
        if not website.startswith("https://"):
            raise forms.ValidationError("Usa un indirizzo https.")
        return website


class CommentForm(forms.Form):
    body = forms.CharField(
        label="Commento", max_length=3000, widget=forms.Textarea(attrs={"rows": 3})
    )


class DecisionForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[("approve", "Approva"), ("changes", "Richiedi modifiche")]
    )
    reason = forms.CharField(label="Motivazione", max_length=3000, required=False)
    revision = forms.IntegerField(min_value=0)

    def clean(self):
        data = super().clean()
        if data.get("decision") == "changes" and not data.get("reason", "").strip():
            self.add_error("reason", "Per richiedere modifiche serve una motivazione.")
        return data
