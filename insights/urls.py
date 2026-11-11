from django.urls import path

from . import engagement, views

app_name = "insights"

urlpatterns = [
    path("risultati/", views.dashboard, name="dashboard"),
    path("api/intenti/", engagement.intent_state, name="intent_state"),
    path("api/intenti/importa/", engagement.import_intents, name="import_intents"),
    path("api/interessi/<int:pk>/", engagement.activity_interest, name="interest"),
    path("api/percorsi/<int:pk>/segui/", engagement.track_follow, name="follow"),
    path("api/attivita/<int:pk>/visita/", views.activity_view, name="activity_view"),
]
