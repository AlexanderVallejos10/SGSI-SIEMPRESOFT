from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Núcleo SGSI"

    def ready(self):
        from apps.core import deletion_protection  # noqa: F401