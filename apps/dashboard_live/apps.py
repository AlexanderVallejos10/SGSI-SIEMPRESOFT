from django.apps import AppConfig


class DashboardLiveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard_live"
    verbose_name = "Dashboard SGSI interactivo"

    def ready(self):
        from . import signals  # noqa: F401
