from django.urls import path

from . import views_accounts as accounts
from . import views_catalog as catalog
from . import views_management as management
from . import views_organizations as organizations
from . import views_progress as progress
from . import views_proposals as proposals
from . import views_review as review
from . import views_tracks as tracks

urlpatterns = [
    path("", catalog.home, name="home"),
    path("attivita/<int:pk>/", catalog.detail, name="activity"),
    path("attivita/<int:pk>/copertina/", catalog.cover, name="cover"),
    path("enti/", catalog.organizations, name="organizations"),
    path("account/enti/", organizations.my_organizations, name="my_organizations"),
    path("account/enti/<int:pk>/", organizations.edit_organization, name="edit_org"),
    path("enti/<int:pk>/logo/", organizations.logo, name="org_logo"),
    path("gestione/", management.overview, name="management"),
    path("gestione/persone/<int:pk>/ruolo/", management.role, name="manage_role"),
    path("gestione/percorsi/nuovo/", tracks.edit_track, name="new_track"),
    path("gestione/percorsi/<int:pk>/", tracks.edit_track, name="edit_track"),
    path("percorsi/", catalog.tracks, name="tracks"),
    path("percorsi/<slug:slug>/", catalog.tracks, name="track"),
    path("registrati/", accounts.register, name="register"),
    path("registrati/ente/", accounts.register_org, name="register_org"),
    path("progressi/", progress.progress_page, name="progress"),
    path("api/progress/", progress.progress_api, name="progress_api"),
    path("demo/<str:role>/", accounts.demo_login, name="demo_login"),
    path("dashboard/", proposals.dashboard, name="dashboard"),
    path("proposte/nuova/", proposals.edit, name="propose"),
    path("proposte/<int:pk>/modifica/", proposals.edit, name="edit_proposal"),
    path("proposte/<int:pk>/commenta/", proposals.comment, name="comment"),
    path("revisione/", review.review_queue, name="review_queue"),
    path("revisione/<int:pk>/decisione/", review.decide, name="decide"),
    path("enti/<int:pk>/verifica/", management.organization_decision, name="verify_org"),
]
