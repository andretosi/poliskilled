from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from .models import Track
from .permissions import is_reviewer


class TrackForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = ["title", "description"]
        labels = {"title": "Nome del percorso", "description": "Descrizione breve"}
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}


@require_http_methods(["GET", "POST"])
def edit_track(request, pk=None):
    if not is_reviewer(request.user):
        raise PermissionDenied
    instance = get_object_or_404(Track, pk=pk) if pk else None
    form = TrackForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        track = form.save(commit=False)
        if not track.pk:
            # Keep the URL stable on renames; the primary key also selects its color.
            from django.db import transaction

            with transaction.atomic():
                base = slugify(track.title)[:40] or "percorso"
                slug, counter = base, 2
                while Track.objects.filter(slug=slug).exists():
                    slug = f"{base}-{counter}"
                    counter += 1
                track.slug = slug
                track.save()
        else:
            track.save()
        messages.success(request, "Percorso salvato. Le attività approvate comporranno la mappa.")
        return redirect("track", slug=track.slug)
    return render(request, "hub/track_form.html", {"form": form, "track": instance})
