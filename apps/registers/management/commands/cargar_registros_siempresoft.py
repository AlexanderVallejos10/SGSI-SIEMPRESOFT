"""Carga las filas reales de los 29 registros del SGSI desde apps/registers/data/registros_siempresoft.json.

Por defecto solo llena los registros (y años) que todavía están vacíos, para no pisar lo que ya se
editó en pantalla. Con --reemplazar, las filas del paquete reemplazan a las existentes de ese año."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.registers.models import RegisterEntry, RegisterImport
from apps.registers.schemas import get

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "registros_siempresoft.json"


class Command(BaseCommand):
    help = "Carga las filas reales de los registros del SGSI de SiempreSoft."

    def add_arguments(self, parser):
        parser.add_argument("--archivo", default=str(DEFAULT_FILE))
        parser.add_argument("--reemplazar", action="store_true", help="Reemplaza las filas existentes del mismo año.")

    def handle(self, *args, **opts):
        path = Path(opts["archivo"])
        if not path.exists():
            raise CommandError(f"No existe el paquete: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        loaded = skipped = 0
        with transaction.atomic():
            for slug, block in data.items():
                if get(slug) is None:
                    self.stdout.write(self.style.WARNING(f"  {slug}: registro desconocido, se omite"))
                    continue
                by_year = {}
                for row in block["rows"]:
                    by_year.setdefault(row["year"], []).append(row)
                for year, rows in by_year.items():
                    existing = RegisterEntry.objects.filter(register=slug, year=year)
                    if existing.exists() and not opts["reemplazar"]:
                        skipped += len(rows)
                        continue
                    existing.delete()
                    RegisterEntry.objects.bulk_create([
                        RegisterEntry(register=slug, year=year, section=r["section"], data=r["data"], order=i + 1)
                        for i, r in enumerate(rows)
                    ])
                    RegisterImport.objects.create(register=slug, year=year, file_name=block.get("source", "")[:255],
                                                  rows=len(rows), replaced=bool(opts["reemplazar"]),
                                                  notes="Carga inicial desde el repositorio de SiempreSoft.")
                    loaded += len(rows)
                self.stdout.write(f"  {slug}: {len(block['rows'])} filas")
        self.stdout.write(self.style.SUCCESS(
            f"Registros cargados: {loaded} filas" + (f" (se omitieron {skipped} de años que ya tenían datos)" if skipped else "")))
