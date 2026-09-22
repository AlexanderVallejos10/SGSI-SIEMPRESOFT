from django.apps import AppConfig


class AuditlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auditlog"
    verbose_name = "Bitácora SGSI"

    def ready(self):
        from apps.auditlog import signals  # noqa: F401