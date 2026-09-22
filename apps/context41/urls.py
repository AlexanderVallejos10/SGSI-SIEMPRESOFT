from django.urls import path

from . import views


app_name = "context41"


urlpatterns = [
    path(
        "sgsi/4.1/",
        views.context41,
        name="home",
    ),
    path(
        "sgsi/4.1/documentos/<slug:slug>/nueva-version/",
        views.upload_version,
        name="upload_version",
    ),
]
