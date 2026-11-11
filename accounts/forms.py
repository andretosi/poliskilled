from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import AccountProfile, normalize_email
from .services import profile_for

UPDATES_LABEL = "Tienimi nel giro: novità e attività del Poli"


def available_email(value, user=None):
    email = normalize_email(value)
    profiles = AccountProfile.objects.filter(email=email)
    users = User.objects.filter(email__iexact=email)
    if user:
        profiles = profiles.exclude(user=user)
        users = users.exclude(pk=user.pk)
    legacy = User.objects.filter(accountprofile__isnull=True).exclude(email="")
    if user:
        legacy = legacy.exclude(pk=user.pk)
    if (
        profiles.exists()
        or users.exists()
        or any(normalize_email(value) == email for value in legacy.values_list("email", flat=True))
    ):
        raise forms.ValidationError("Questa email è già associata a un account.")
    return email


class EmailRegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Email", max_length=254)
    updates_opt_in = forms.BooleanField(
        label=UPDATES_LABEL,
        required=False,
        initial=False,
        help_text="Facoltativo. Puoi cambiare idea dalle impostazioni account, quando vuoi.",
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "updates_opt_in")

    def clean_email(self):
        return available_email(self.cleaned_data["email"])

    def save(self, commit=True):
        if not commit:
            raise ValueError("Account registration must be saved atomically.")
        with transaction.atomic():
            user = super().save()
            opted_in = self.cleaned_data["updates_opt_in"]
            AccountProfile.objects.create(
                user=user,
                email=user.email,
                updates_opt_in=opted_in,
                consent_at=timezone.now() if opted_in else None,
            )
        return user


class ProfileForm(forms.ModelForm):
    updates_opt_in = forms.BooleanField(
        label=UPDATES_LABEL,
        required=False,
        help_text="Facoltativo. Togli la spunta per non ricevere più aggiornamenti.",
    )

    class Meta:
        model = User
        fields = ("username", "updates_opt_in")
        help_texts = {"username": ""}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile_for(self.instance)
        self.fields["updates_opt_in"].initial = self.profile.updates_opt_in

    @transaction.atomic
    def save(self, commit=True):
        # Lock and update only owned fields, preserving concurrent password/email changes.
        user = User.objects.select_for_update().get(pk=self.instance.pk)
        user.username = self.cleaned_data["username"]
        user.save(update_fields=["username"])
        profile = AccountProfile.objects.select_for_update().get(pk=self.profile.pk)
        opted_in = self.cleaned_data["updates_opt_in"]
        if opted_in and not profile.updates_opt_in:
            profile.consent_at = timezone.now()
        if not opted_in:
            profile.consent_at = None
        profile.updates_opt_in = opted_in
        profile.save(update_fields=["updates_opt_in", "consent_at"])
        return user


class EmailChangeForm(forms.Form):
    email = forms.EmailField(label="Nuova email", max_length=254)
    current_password = forms.CharField(
        label="Password attuale", strip=False, widget=forms.PasswordInput
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        password = self.cleaned_data["current_password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("La password attuale non è corretta.")
        return password

    def clean_email(self):
        email = available_email(self.cleaned_data["email"], self.user)
        if email == profile_for(self.user).email:
            raise forms.ValidationError("Questa è già la tua email. Puoi confermarla qui sotto.")
        return email
