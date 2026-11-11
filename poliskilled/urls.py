from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("privacy/", TemplateView.as_view(template_name="privacy.html"), name="privacy"),
    path("", include("accounts.urls")),
    path("", include("insights.urls")),
    path("admin/", admin.site.urls),
    path("accedi/", auth.LoginView.as_view(template_name="hub/login.html"), name="login"),
    path("esci/", auth.LogoutView.as_view(), name="logout"),
    path("", include("hub.urls")),
]
