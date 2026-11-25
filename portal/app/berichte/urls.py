from django.urls import path

from . import views

app_name = "berichte"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("kennzahlen/", views.kennzahlen, name="kennzahlen"),
]
