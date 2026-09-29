from django.contrib import admin
from django.urls import include, path

from apps.traceability.media import protected_media

urlpatterns = [
    path("trazabilidad/", include("apps.traceability.urls")),
    path("", include("apps.dashboard_live.urls")),
    path("", include("apps.processes.urls")),
    path("", include("apps.context42.urls")),
    path("", include("apps.context41.urls")),
    path("organizacion/", include("apps.organization.urls")),
    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "",
        include("apps.accounts.urls"),
    ),

    path(
        "",
        include("apps.dashboard.urls"),
    ),
    path("media/<path:path>", protected_media, name="protected_media"),
]
