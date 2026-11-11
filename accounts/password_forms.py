from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm


class PasswordOnlySave:
    def save(self, commit=True):
        # Confirmation/profile updates can race with an already validated form.
        # Never persist unrelated fields from that older User instance.
        self.user.set_password(self.cleaned_data["new_password1"])
        if commit:
            self.user.save(update_fields=["password"])
        return self.user


class PasswordChangeForm(PasswordOnlySave, DjangoPasswordChangeForm):
    pass


class SetPasswordForm(PasswordOnlySave, DjangoSetPasswordForm):
    pass
