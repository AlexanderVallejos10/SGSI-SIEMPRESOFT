from django.urls import path

from . import views


app_name = "processes"


urlpatterns = [
    path(
        "procesos/",
        views.process_map,
        name="map",
    ),
    path(
        "sgsi/4.3/",
        views.process_map,
        name="context43",
    ),
    path(
        "procesos/nuevo/",
        views.process_create,
        name="process_create",
    ),
    path(
        "procesos/<uuid:pk>/",
        views.process_detail,
        name="process_detail",
    ),
    path(
        "procesos/<uuid:pk>/editar/",
        views.process_edit,
        name="process_edit",
    ),
    path(
        "procesos/<uuid:pk>/retirar/",
        views.process_archive,
        name="process_archive",
    ),
    path(
        "procesos/relaciones/nueva/",
        views.relation_create,
        name="relation_create",
    ),
    path(
        "procesos/relaciones/<uuid:pk>/retirar/",
        views.relation_archive,
        name="relation_archive",
    ),
    path(
        "procesos/mapa/guardar/",
        views.save_layout,
        name="save_layout",
    ),
    path(
        "procesos/documentos/<slug:slug>/nueva-version/",
        views.reference_upload,
        name="reference_upload",
    ),
    path(
        "procesos/documentos/version/<uuid:pk>/ver/",
        views.reference_version_view,
        name="reference_view",
    ),
    path(
        "procesos/documentos/version/<uuid:pk>/descargar/",
        views.reference_version_download,
        name="reference_download",
    ),
]
