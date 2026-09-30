from django.urls import path

from . import views

app_name = "registers"

urlpatterns = [
    path("", views.index, name="index"),
    path("<slug:slug>/", views.detail, name="detail"),
    path("<slug:slug>/filas/nueva/", views.create_row, name="create_row"),
    path("<slug:slug>/importar/", views.import_excel, name="import"),
    path("<slug:slug>/descargar/", views.export_excel, name="export"),
    path("filas/<int:pk>/", views.update_row, name="update_row"),
    path("filas/<int:pk>/eliminar/", views.delete_row, name="delete_row"),
]
