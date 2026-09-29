from django.urls import path

from . import views

app_name = "organization"

urlpatterns = [
    path(
        "",
        views.chart,
        name="chart",
    ),
    path(
        "puestos/nuevo/",
        views.position_create,
        name="position_create",
    ),
    path(
        "puestos/<uuid:pk>/editar/",
        views.position_edit,
        name="position_edit",
    ),
    path(
        "puestos/<uuid:pk>/mover/",
        views.position_move,
        name="position_move",
    ),
    path(
        "puestos/<uuid:pk>/asignar/",
        views.assign_user,
        name="assign_user",
    ),
    path(
        "puestos/<uuid:pk>/nuevo-usuario/",
        views.quick_user_create,
        name="quick_user_create",
    ),
    path(
        "puestos/<uuid:pk>/desactivar/",
        views.position_archive,
        name="position_archive",
    ),
    path(
        "asignaciones/<uuid:pk>/cerrar/",
        views.assignment_close,
        name="assignment_close",
    ),
    path(
        "areas/",
        views.areas,
        name="areas",
    ),
    path(
        "areas/nueva/",
        views.area_create,
        name="area_create",
    ),
    path(
        "areas/<uuid:pk>/editar/",
        views.area_edit,
        name="area_edit",
    ),
    path("areas/<uuid:pk>/", views.area_detail, name="area_detail"),
]
