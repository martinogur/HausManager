from django.urls import path

from . import views

app_name = "cockpit"

urlpatterns = [
    path("menue/", views.menue, name="menue"),
    path("freigaben/", views.freigaben_liste, name="freigaben"),
    path("freigaben/<uuid:pk>/", views.freigaben_detail, name="freigaben_detail"),
    path("agenten/", views.agenten, name="agenten"),
    path("agenten/starten/", views.agenten_starten, name="agenten_starten"),
    path("agenten/<str:code>/schalten/", views.agenten_schalten, name="agenten_schalten"),
    path("agenten/auftrag/<uuid:pk>/", views.agenten_auftrag, name="agenten_auftrag"),
    path("automatisierungen/", views.automatisierungen, name="automatisierungen"),
    path("automatisierungen/<str:code>/schalten/", views.automatisierungen_schalten, name="automatisierungen_schalten"),
    path("akquise/", views.akquise, name="akquise"),
    path("akquise/neu/", views.akquise_neu, name="akquise_neu"),
    path("akquise/<uuid:pk>/", views.akquise_lead, name="akquise_lead"),
    path("angebote/rechner/", views.angebot_rechner, name="angebot_rechner"),
    path("auftraege/", views.auftraege, name="auftraege"),
    path("auftraege/<uuid:pk>/", views.auftraege_detail, name="auftraege_detail"),
    path("controlling/", views.controlling_ansicht, name="controlling"),
    path("marketing/", views.marketing, name="marketing"),
    path("einsatz/<uuid:pk>/", views.einsatz, name="einsatz"),
    path("foto/<uuid:pk>/", views.foto, name="foto"),
]
