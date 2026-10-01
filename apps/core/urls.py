from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.resultados, name="buscar"),
    path("sugerencias/", views.sugerencias, name="sugerencias"),
]
