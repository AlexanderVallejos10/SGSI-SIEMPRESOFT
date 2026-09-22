from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.dashboard_live.importer import import_workbook, workbook_summary


SOURCE = Path(
    "/app/imports/Dashboard SGSI de SIEMPRESOFT_3.xlsx"
)


class Command(BaseCommand):
    help = "Importa el Dashboard SGSI real como datos editables y trazables."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        if not SOURCE.is_file():
            raise CommandError(f"No existe: {SOURCE}")

        summary = workbook_summary(SOURCE)
        self.stdout.write("=== DASHBOARD SGSI LIVE ===")
        self.stdout.write("Modo: " + ("APPLY" if options["apply"] else "PREVIEW"))
        for key, value in summary.items():
            self.stdout.write(f"{key}: {value}")

        if not options["apply"]:
            self.stdout.write("PREVIEW: no se modificó PostgreSQL.")
            return

        dataset = import_workbook(
            path=SOURCE,
            version_label="2026",
            notes="Carga inicial del Dashboard SGSI de SIEMPRESOFT.",
            apply_changes=True,
        )
        self.stdout.write(
            self.style.SUCCESS(f"Dashboard importado. Dataset: {dataset.code}")
        )
