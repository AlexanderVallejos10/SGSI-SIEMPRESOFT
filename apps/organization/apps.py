from django.apps import AppConfig


class OrganizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.organization"
    verbose_name = "Organización y estructura"

    def ready(self):
        from . import signals  # noqa: F401
