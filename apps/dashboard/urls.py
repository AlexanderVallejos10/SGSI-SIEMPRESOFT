
from django.urls import path

from . import manual_reference, views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("health/", views.health, name="health"),
    path("reportes/", views.report_center, name="report_center"),
    path("sgsi/manual/registrar/", views.register_manual_document, name="manual_register"),
    path("manual-sgsi/version/", manual_reference.update_manual_reference, name="manual_reference_update"),
    path("sgsi/<str:code>/", views.clause_detail, name="clause_detail"),
    path("anexos/", views.annex_controls, name="annex_controls"),
    path("organizacion/", views.organization, name="organization"),
    path("usuarios/<str:pk>/", views.user_profile, name="user_profile"),
    path("controles/<str:pk>/", views.control_detail, name="control_detail"),
    path("gestion/<slug:entity>/", views.entity_list, name="entity_list"),
    path("gestion/<slug:entity>/nuevo/", views.entity_add, name="entity_add"),
    path("gestion/<slug:entity>/<str:pk>/", views.entity_detail, name="entity_detail"),
    path("gestion/<slug:entity>/<str:pk>/editar/", views.entity_edit, name="entity_edit"),
    path("documentos/<uuid:document_id>/", views.document_detail, name="document_detail"),
    path("documentos/versiones/<uuid:version_id>/ver/", views.version_file, name="version_file"),
    path("documentos/versiones/<uuid:version_id>/descargar/", views.version_download, name="version_download"),
    path("documentos/versiones/<uuid:version_id>/tabla/", views.version_table, name="version_table"),
    path("archivos/<uuid:artifact_id>/tabla/", views.artifact_table, name="artifact_table"),
    path("archivos/<uuid:artifact_id>/ver/", views.artifact_view, name="artifact_view"),
    path("archivos/<uuid:artifact_id>/descargar/", views.artifact_download, name="artifact_download"),
]
