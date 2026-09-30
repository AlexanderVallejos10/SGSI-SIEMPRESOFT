from django.urls import path

from . import views

app_name = "assets"

urlpatterns = [
    path("", views.asset_list, name="list"),
    path("exportar/", views.inventory_export, name="export"),
    path("<str:code>/", views.asset_detail, name="detail"),
]
