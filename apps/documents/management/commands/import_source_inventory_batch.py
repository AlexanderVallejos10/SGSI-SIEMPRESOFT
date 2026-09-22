import os
from fnmatch import fnmatch
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.documents.models import SourceArtifact, SourcePackage


class Command(BaseCommand):
    help = (
        "Procesa por lotes los ZIP de una carpeta usando "
        "import_source_inventory, conservando la detección "
        "de duplicados entre paquetes del mismo lote."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "directory",
            help=(
                "Carpeta dentro del contenedor que contiene "
                "los ZIP. Ejemplo: /app/imports"
            ),
        )
        parser.add_argument(
            "--pattern",
            default="OneDrive_2026-09-16*.zip",
            help=(
                "Patrón de nombres a procesar. "
                "Por defecto: OneDrive_2026-09-16*.zip"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Procesa todo el lote dentro de una única "
                "transacción y revierte al finalizar."
            ),
        )
        parser.add_argument(
            "--show-files",
            action="store_true",
            help=(
                "Muestra también la salida individual de "
                "cada archivo procesado."
            ),
        )
        parser.add_argument(
            "--max-uncompressed-mb",
            type=int,
            default=8192,
            help=(
                "Límite de seguridad por ZIP para tamaño "
                "total descomprimido. Por defecto: 8192 MB."
            ),
        )
        parser.add_argument(
            "--stop-on-error",
            action="store_true",
            help="Detiene el lote en el primer ZIP con error.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        directory = os.path.abspath(options["directory"])
        pattern = options["pattern"]
        dry_run = options["dry_run"]
        show_files = options["show_files"]
        max_uncompressed_mb = options["max_uncompressed_mb"]
        stop_on_error = options["stop_on_error"]

        if not os.path.isdir(directory):
            raise CommandError(
                f"No existe la carpeta: {directory}"
            )

        zip_names = sorted(
            name
            for name in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, name))
            and fnmatch(name, pattern)
        )

        if not zip_names:
            raise CommandError(
                "No se encontraron ZIP que coincidan con "
                f"el patrón {pattern!r} en {directory}"
            )

        before_packages = SourcePackage.objects.count()
        before_artifacts = SourceArtifact.objects.count()

        successes = []
        errors = []

        self.stdout.write(
            f"Carpeta: {directory}"
        )
        self.stdout.write(
            f"Patrón: {pattern}"
        )
        self.stdout.write(
            f"ZIP encontrados: {len(zip_names)}"
        )
        self.stdout.write(
            f"Paquetes antes: {before_packages}"
        )
        self.stdout.write(
            f"Archivos antes: {before_artifacts}"
        )
        self.stdout.write("")

        for index, zip_name in enumerate(zip_names, start=1):
            zip_path = os.path.join(directory, zip_name)

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"[{index}/{len(zip_names)}] {zip_name}"
                )
            )

            buffer = StringIO()

            try:
                call_command(
                    "import_source_inventory",
                    zip_path,
                    dry_run=False,
                    show_files=show_files,
                    max_uncompressed_mb=max_uncompressed_mb,
                    stdout=buffer,
                    stderr=buffer,
                )

                output = buffer.getvalue().strip()

                if output:
                    if show_files:
                        self.stdout.write(output)
                    else:
                        selected = []
                        for line in output.splitlines():
                            if (
                                line.startswith("PAQUETE |")
                                or line.startswith("PAQUETE DUPLICADO DE |")
                                or line.startswith("Paquete:")
                                or line.startswith("SHA-256 ZIP:")
                                or line.startswith("Manifest SHA-256:")
                                or line.startswith("Duplicado de:")
                                or line.startswith("Archivos:")
                                or line.startswith("Creados:")
                                or line.startswith("Actualizados:")
                                or line.startswith("Duplicados detectados:")
                                or line.startswith("Inválidos:")
                            ):
                                selected.append(line)

                        if selected:
                            self.stdout.write(
                                "\n".join(selected)
                            )

                successes.append(zip_name)

            except Exception as exc:
                errors.append(
                    (zip_name, f"{exc.__class__.__name__}: {exc}")
                )

                self.stderr.write(
                    self.style.ERROR(
                        f"ERROR | {zip_name} | "
                        f"{exc.__class__.__name__}: {exc}"
                    )
                )

                if stop_on_error:
                    raise

            self.stdout.write("")

        after_packages = SourcePackage.objects.count()
        after_artifacts = SourceArtifact.objects.count()

        duplicate_packages = (
            SourcePackage.objects
            .filter(duplicate_of__isnull=False)
            .count()
        )
        duplicate_artifacts = (
            SourceArtifact.objects
            .filter(duplicate_of__isnull=False)
            .count()
        )
        invalid_artifacts = (
            SourceArtifact.objects
            .filter(quality_status="invalid")
            .count()
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Resumen del inventario por lotes"
            )
        )
        self.stdout.write(
            f"ZIP procesados correctamente: {len(successes)}"
        )
        self.stdout.write(
            f"ZIP con error: {len(errors)}"
        )
        self.stdout.write(
            f"Paquetes antes: {before_packages}"
        )
        self.stdout.write(
            f"Paquetes después: {after_packages}"
        )
        self.stdout.write(
            f"Nuevos paquetes en el lote: "
            f"{after_packages - before_packages}"
        )
        self.stdout.write(
            f"Paquetes duplicados acumulados: "
            f"{duplicate_packages}"
        )
        self.stdout.write(
            f"Archivos antes: {before_artifacts}"
        )
        self.stdout.write(
            f"Archivos después: {after_artifacts}"
        )
        self.stdout.write(
            f"Nuevos archivos en el lote: "
            f"{after_artifacts - before_artifacts}"
        )
        self.stdout.write(
            f"Archivos duplicados acumulados: "
            f"{duplicate_artifacts}"
        )
        self.stdout.write(
            f"Archivos inválidos acumulados: "
            f"{invalid_artifacts}"
        )

        if errors:
            self.stdout.write("")
            self.stdout.write("ZIP con error:")
            for name, error in errors:
                self.stdout.write(
                    f"- {name}: {error}"
                )

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN DEL LOTE: todos los cambios "
                    "del lote fueron revertidos."
                )
            )
