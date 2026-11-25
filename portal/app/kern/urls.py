from django.urls import path

from . import views

app_name = "kern"

urlpatterns = [
    path("gesund", views.gesund, name="gesund"),
]
