from django.urls import path

from . import views

app_name = "konten"

urlpatterns = [
    path("anmelden/", views.AnmeldenAnsicht.as_view(), name="anmelden"),
    path("abmelden/", views.AbmeldenAnsicht.as_view(), name="abmelden"),
    path("konto/zwei-faktor/einrichten/", views.zwei_faktor_einrichten, name="zwei_faktor_einrichten"),
    path("konto/zwei-faktor/code/", views.zwei_faktor_pruefen, name="zwei_faktor_pruefen"),
]
