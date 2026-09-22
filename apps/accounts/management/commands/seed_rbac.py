from django.core.management.base import BaseCommand

from apps.accounts.rbac import sync_rbac_roles


class Command(BaseCommand):
    help = "Crea o actualiza los roles y permisos iniciales del SGSI"

    def handle(self, *args, **options):
        self.stdout.write("Sincronizando RBAC del SGSI...")

        results = sync_rbac_roles()

        for role_name, permission_count in results.items():
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK - {role_name}: {permission_count} permisos"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "RBAC del SGSI sincronizado correctamente."
            )
        )