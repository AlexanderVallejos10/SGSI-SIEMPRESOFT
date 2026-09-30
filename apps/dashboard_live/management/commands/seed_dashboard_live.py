"""Importa el Excel del Dashboard SGSI.

    python manage.py seed_dashboard_live --apply [--archivo RUTA] [--version 2026]

Por defecto usa el Excel 2026 real que viene con el sistema. La versión se toma del nombre del archivo
(p. ej. «_2026»); nunca se etiqueta como 2026 un archivo de otro año."""

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.dashboard_live.importer import import_workbook, workbook_summary

DEFAULT = Path(settings.BASE_DIR) / "apps" / "dashboard" / "data" / "documentos" / "Dashboard SGSI de SIEMPRESOFT_2026.xlsx"


def version_from_name(path):
    match = re.search(r"(20\d\d)", path.stem)
    return match.group(1) if match else "sin año"


class Command(BaseCommand):
    help = "Importa el Dashboard SGSI como datos editables y trazables."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--archivo", default=str(DEFAULT))
        parser.add_argument("--version", default="", help="Versión a mostrar; por defecto, el año del nombre del archivo.")

    def handle(self, *args, **options):
        source = Path(options["archivo"])
        if not source.is_file():
            raise CommandError(f"No existe: {source}")
        label = options["version"] or version_from_name(source)
        summary = workbook_summary(source)
        self.stdout.write(f"Archivo: {source.name} (versión {label})")
        for key, value in summary.items():
            self.stdout.write(f"{key}: {value}")
        if not options["apply"]:
            self.stdout.write("Vista previa: no se modificó la base de datos.")
            return
        dataset = import_workbook(path=source, version_label=label, original_name=source.name,
                                  notes=f"Importado desde {source.name}.", apply_changes=True)
        self.stdout.write(self.style.SUCCESS(f"Tablero vigente: {dataset.original_name} (versión {dataset.version_label})."))
