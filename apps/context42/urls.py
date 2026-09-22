from django.urls import path

from . import views

app_name = "context42"

urlpatterns = [
    path("sgsi/4.2/", views.context42_home, name="home"),
    path("sgsi/4.2/<slug:slug>/subir/", views.upload_version, name="upload_version"),
    path("sgsi/4.2/<slug:slug>/descargar/", views.download_current, name="download_current"),
]
