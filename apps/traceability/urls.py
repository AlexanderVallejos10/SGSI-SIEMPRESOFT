from django.urls import path

from . import views

app_name = "traceability"
urlpatterns = [
    path("riesgos/vincular/", views.risk_link_many, name="risk_link_many"),
    path("riesgos/", views.risks, name="risks"),
    path("riesgos/nuevo/", views.risk_edit, name="risk_new"),
    path("riesgos/<uuid:pk>/", views.risk_edit, name="risk_edit"),
    path("documentos/", views.links, name="links"),
    path("documentos/nuevo/", views.link_edit, name="link_new"),
    path("documentos/<uuid:pk>/", views.link_edit, name="link_edit"),
    path("importar/", views.workbook_upload, name="import"),
    path("fuentes/", views.source_rows, name="sources"),
    path("personas/<uuid:user_id>/acta/", views.handover_edit, name="handover_new"),
    path("actas/<uuid:pk>/", views.handover_detail, name="handover_detail"),
    path("actas/<uuid:pk>/editar/", views.handover_edit, name="handover_edit"),
    path("actas/<uuid:pk>/emitir/", views.handover_issue, name="handover_issue"),
    path("actas/<uuid:pk>/docx/", views.handover_download, name="handover_download"),
    path("actas/<uuid:pk>/firmar/", views.handover_signed, name="handover_signed"),
    path("actas/<uuid:pk>/firmada/", views.signed_download, name="signed_download"),
]
