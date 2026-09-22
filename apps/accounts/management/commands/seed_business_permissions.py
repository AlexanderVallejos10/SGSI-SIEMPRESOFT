from django.core.management.base import BaseCommand

from apps.accounts.business_permissions import sync_business_permissions


class Command(BaseCommand):
    help = "Crea y sincroniza los permisos específicos del negocio SGSI"

    def handle(self, *args, **options):
        self.stdout.write(
            "Sincronizando permisos de negocio del SGSI..."
        )

        result = sync_business_permissions()

        self.stdout.write(
            self.style.SUCCESS(
                f"Permisos creados: {result['created']}"
            )
        )

        self.stdout.write(
            f"Permisos existentes/actualizados: {result['existing']}"
        )

        self.stdout.write("")

        for role_name, count in result["roles"].items():
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK - {role_name}: "
                    f"{count} permisos de negocio"
                )
            )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Permisos de negocio SGSI sincronizados correctamente."
            )
        )