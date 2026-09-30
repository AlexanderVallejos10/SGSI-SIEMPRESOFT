"""Carga todo lo real de SiempreSoft de una vez: los 29 registros del SGSI y los activos con su historial."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Carga registros del SGSI y activos reales de SiempreSoft."

    def add_arguments(self, parser):
        parser.add_argument("--reemplazar", action="store_true", help="Reemplaza las filas de registros ya cargadas.")

    def handle(self, *args, **opts):
        self.stdout.write("1/2 Registros del SGSI")
        call_command("cargar_registros_siempresoft", reemplazar=opts["reemplazar"], stdout=self.stdout)
        self.stdout.write("2/2 Activos, colaboradores e historial")
        call_command("cargar_activos_siempresoft", stdout=self.stdout)
