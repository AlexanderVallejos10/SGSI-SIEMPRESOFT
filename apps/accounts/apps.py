from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        from . import signals_access  # noqa: F401  (registro de ingresos, salidas e intentos)
