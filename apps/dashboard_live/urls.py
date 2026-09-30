from django.urls import path
from . import views

app_name = "dashboard_live"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard-sgsi/", views.home, name="dashboard"),
    path("dashboard-sgsi/datos.json", views.dashboard_data, name="data"),
    path("dashboard-sgsi/sgsi/<uuid:pk>/editar/", views.edit_sgsi_metric, name="edit_sgsi_metric"),
    path("dashboard-sgsi/oesi/<uuid:pk>/editar/", views.edit_oesi_metric, name="edit_oesi_metric"),
    path("dashboard-sgsi/factor/<uuid:pk>/editar/", views.edit_factor, name="edit_factor"),
    path("dashboard-sgsi/oee-osi/<uuid:pk>/toggle/", views.toggle_oee_alignment, name="toggle_oee_alignment"),
    path("dashboard-sgsi/req-osi/<uuid:pk>/toggle/", views.toggle_req_alignment, name="toggle_req_alignment"),
    path("dashboard-sgsi/descargar/", views.download_updated_workbook, name="download"),
    path("dashboard-sgsi/subir/", views.upload_workbook, name="upload"),
]
