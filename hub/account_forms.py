from django import forms

from accounts.forms import EmailRegistrationForm

from .forms import RegisterForm


class PersonalRegisterForm(EmailRegistrationForm):
    pass


class OrganizationRequestForm(forms.Form):
    organization = RegisterForm.base_fields["organization"]
    website = RegisterForm.base_fields["website"]
    clean_organization = RegisterForm.clean_organization
    clean_website = RegisterForm.clean_website
