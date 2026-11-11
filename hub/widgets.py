from django.forms import ClearableFileInput


class PrivateImageInput(ClearableFileInput):
    template_name = "hub/widgets/private_image.html"
