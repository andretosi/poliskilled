import warnings
from io import BytesIO

from django import forms
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Organization


class OrganizationForm(forms.ModelForm):
    revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    logo = forms.FileField(
        label="Logo",
        required=False,
        help_text="PNG, JPG o WebP · massimo 1 MB.",
        widget=forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
    )
    remove_logo = forms.BooleanField(label="Togli il logo", required=False)

    class Meta:
        model = Organization
        fields = ("name", "short_name", "description", "website", "logo")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean_description(self):
        value = self.cleaned_data["description"]
        if len(value) > 1500:
            raise forms.ValidationError("Rimani entro 1.500 caratteri.")
        return value

    def clean_logo(self):
        upload = self.files.get("logo")
        if not upload:
            return self.instance.logo
        if upload.size > 1024 * 1024:
            raise forms.ValidationError("Il logo deve pesare meno di 1 MB.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(upload) as source:
                    if source.format not in {"PNG", "JPEG", "WEBP"}:
                        raise ValueError
                    if source.width * source.height > 4_000_000:
                        raise ValueError
                    source.load()
                    clean = ImageOps.exif_transpose(source).convert("RGBA")
                    clean.info.clear()
                    clean.thumbnail((512, 512))
                    output = BytesIO()
                    clean.save(output, "PNG")
        except (
            OSError,
            ValueError,
            UnidentifiedImageError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise forms.ValidationError("Scegli un'immagine valida, entro 4 megapixel.") from None
        return ContentFile(output.getvalue(), name="logo.png")

    def clean(self):
        data = super().clean()
        if data.get("remove_logo") and self.files.get("logo"):
            self.add_error("logo", "Scegli se sostituire o togliere il logo.")
        return data
