from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
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
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )