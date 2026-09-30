from django.urls import path

from . import views

app_name = "governance"

urlpatterns = [
    path("revision-direccion/", views.review_list, name="review_list"),
    path("revision-direccion/nueva/", views.review_create, name="review_create"),
    path("revision-direccion/<int:pk>/", views.review_detail, name="review_detail"),
    path("aceptacion-riesgos/", views.acceptance, name="acceptance"),
    path("revision-accesos/", views.access_review, name="access_review"),
    path("declaracion-aplicabilidad/", views.soa, name="soa"),
]
