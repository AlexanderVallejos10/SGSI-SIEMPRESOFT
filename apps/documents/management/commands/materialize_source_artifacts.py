import hashlib
import os
import tempfile
import zipfile
from collections import defaultdict

from django.core.files import File as DjangoFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.documents.models import SourceArtifact


SGSI_RELEVANCE = ("nucleo_sgsi", "soporte_sgsi")


def human_size(value):
    value = int(value or 0)
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def sha256_stream(stream, temp_file=None):
    digest = hashlib.sha256()
    total = 0

    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
        total += len(chunk)
        if temp_file is not None:
            temp_file.write(chunk)

    return digest.hexdigest(), total


class Command(BaseCommand):
    help = (
        "Materializa archivos canónicos desde sus ZIP fuente hacia el "
        "FileField de SourceArtifact, verificando SHA-256. "
        "Por defecto solo previsualiza; use --apply para guardar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "directory",
            nargs="?",
            default="/app/imports",
            help="Carpeta que contiene los ZIP fuente. Por defecto: /app/imports",
        )
        parser.add_argument(
            "--scope",
            choices=("sgsi", "document", "all"),
            default="sgsi",
            help=(
                "sgsi: núcleo/soporte SGSI candidato a documento/evidencia/dashboard; "
                "document: todos los candidatos Document; "
                "all: todos los artefactos canónicos."
            ),
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Guarda físicamente los archivos y actualiza SourceArtifact.file.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Vuelve a materializar artefactos que ya tengan archivo.",
        )
        parser.add_argument(
            "--stop-on-error",
            action="store_true",
            help="Detiene el proceso en el primer error.",
        )
        parser.add_argument(
            "--show-files",
            action="store_true",
            help="Muestra una línea por archivo validado/materializado.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        directory = os.path.abspath(options["directory"])
        scope = options["scope"]
        apply_changes = options["apply"]
        overwrite = options["overwrite"]
        stop_on_error = options["stop_on_error"]
        show_files = options["show_files"]

        if not os.path.isdir(directory):
            raise CommandError(f"No existe la carpeta fuente: {directory}")

        qs = (
            SourceArtifact.objects
            .select_related("source_package", "classification")
            .filter(duplicate_of__isnull=True)
            .exclude(source_package__isnull=True)
        )

        if scope == "sgsi":
            qs = qs.filter(
                classification__sgsi_relevance__in=SGSI_RELEVANCE,
            ).filter(
                Q(classification__is_document_candidate=True)
                | Q(classification__is_evidence_candidate=True)
                | Q(classification__is_dashboard_candidate=True)
            )
        elif scope == "document":
            qs = qs.filter(
                classification__is_document_candidate=True
            )

        if not overwrite:
            qs = qs.filter(Q(file="") | Q(file__isnull=True))

        artifacts = list(
            qs.order_by(
                "source_package__original_name",
                "original_path",
            )
        )

        grouped = defaultdict(list)
        for artifact in artifacts:
            grouped[artifact.source_package_id].append(artifact)

        total_bytes = sum(int(a.size_bytes or 0) for a in artifacts)

        self.stdout.write("=== MATERIALIZACIÓN DE FUENTES ===")
        self.stdout.write(f"Modo: {'APPLY' if apply_changes else 'PREVIEW'}")
        self.stdout.write(f"Scope: {scope}")
        self.stdout.write(f"Artefactos seleccionados: {len(artifacts)}")
        self.stdout.write(f"Tamaño declarado: {human_size(total_bytes)}")
        self.stdout.write(f"Paquetes implicados: {len(grouped)}")
        self.stdout.write("")

        validated = 0
        saved = 0
        skipped = 0
        errors = []

        packages = {}
        for artifact in artifacts:
            packages[artifact.source_package_id] = artifact.source_package

        for package_id, package_artifacts in grouped.items():
            package = packages[package_id]
            zip_path = os.path.join(directory, package.original_name)

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"PAQUETE | {package.code} | {package.original_name} | "
                    f"{len(package_artifacts)} artefactos"
                )
            )

            if not os.path.isfile(zip_path):
                message = f"No existe el ZIP fuente: {zip_path}"
                errors.append((package.original_name, message))
                self.stderr.write(self.style.ERROR(f"ERROR | {message}"))
                if stop_on_error:
                    raise CommandError(message)
                continue

            if not zipfile.is_zipfile(zip_path):
                message = f"El archivo fuente no es un ZIP válido: {zip_path}"
                errors.append((package.original_name, message))
                self.stderr.write(self.style.ERROR(f"ERROR | {message}"))
                if stop_on_error:
                    raise CommandError(message)
                continue

            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    names = set(zf.namelist())

                    for artifact in package_artifacts:
                        try:
                            if artifact.original_path not in names:
                                raise KeyError(
                                    f"No se encontró dentro del ZIP: "
                                    f"{artifact.original_path}"
                                )

                            info = zf.getinfo(artifact.original_path)

                            if info.is_dir():
                                raise ValueError(
                                    "El artefacto apunta a un directorio, no a un archivo."
                                )

                            if int(artifact.size_bytes or 0) not in (0, info.file_size):
                                raise ValueError(
                                    f"Tamaño distinto. DB={artifact.size_bytes}, "
                                    f"ZIP={info.file_size}"
                                )

                            if apply_changes:
                                temp = tempfile.NamedTemporaryFile(
                                    mode="w+b",
                                    delete=False,
                                )
                                temp_path = temp.name

                                try:
                                    with zf.open(info, "r") as source:
                                        digest, actual_size = sha256_stream(
                                            source,
                                            temp_file=temp,
                                        )

                                    temp.flush()
                                    temp.close()

                                    if digest != artifact.checksum_sha256:
                                        raise ValueError(
                                            "SHA-256 no coincide. "
                                            f"DB={artifact.checksum_sha256}, "
                                            f"actual={digest}"
                                        )

                                    if actual_size != info.file_size:
                                        raise ValueError(
                                            f"Lectura incompleta: "
                                            f"{actual_size} != {info.file_size}"
                                        )

                                    storage_name = (
                                        f"{artifact.code}_"
                                        f"{os.path.basename(artifact.original_name)}"
                                    )

                                    with open(temp_path, "rb") as ready:
                                        artifact.file.save(
                                            storage_name,
                                            DjangoFile(ready),
                                            save=False,
                                        )

                                    artifact.source_verified = True
                                    artifact.save(
                                        update_fields=(
                                            "file",
                                            "source_verified",
                                            "updated_at",
                                        )
                                    )
                                    saved += 1
                                finally:
                                    try:
                                        temp.close()
                                    except Exception:
                                        pass
                                    try:
                                        os.unlink(temp_path)
                                    except Exception:
                                        pass
                            else:
                                with zf.open(info, "r") as source:
                                    digest, actual_size = sha256_stream(source)

                                if digest != artifact.checksum_sha256:
                                    raise ValueError(
                                        "SHA-256 no coincide. "
                                        f"DB={artifact.checksum_sha256}, "
                                        f"actual={digest}"
                                    )

                                if actual_size != info.file_size:
                                    raise ValueError(
                                        f"Lectura incompleta: "
                                        f"{actual_size} != {info.file_size}"
                                    )

                            validated += 1

                            if show_files:
                                action = "GUARDADO" if apply_changes else "VALIDADO"
                                self.stdout.write(
                                    f"{action} | {artifact.code} | "
                                    f"{human_size(info.file_size)} | "
                                    f"{artifact.original_path}"
                                )

                        except Exception as exc:
                            message = (
                                f"{artifact.code} | {artifact.original_path} | "
                                f"{exc.__class__.__name__}: {exc}"
                            )
                            errors.append((package.original_name, message))
                            self.stderr.write(
                                self.style.ERROR(f"ERROR | {message}")
                            )
                            if stop_on_error:
                                raise

            except Exception as exc:
                if stop_on_error:
                    raise
                if not isinstance(exc, (zipfile.BadZipFile, OSError)):
                    continue
                message = (
                    f"{package.original_name} | "
                    f"{exc.__class__.__name__}: {exc}"
                )
                errors.append((package.original_name, message))
                self.stderr.write(self.style.ERROR(f"ERROR | {message}"))

        self.stdout.write("")
        self.stdout.write("=== RESUMEN ===")
        self.stdout.write(f"Seleccionados: {len(artifacts)}")
        self.stdout.write(f"Validados SHA-256: {validated}")
        self.stdout.write(f"Materializados: {saved}")
        self.stdout.write(f"Omitidos: {skipped}")
        self.stdout.write(f"Errores: {len(errors)}")

        if errors:
            self.stdout.write("")
            self.stdout.write("=== ERRORES ===")
            for package_name, message in errors[:100]:
                self.stdout.write(f"- {package_name}: {message}")
            if len(errors) > 100:
                self.stdout.write(
                    f"... {len(errors) - 100} errores adicionales omitidos."
                )

        if not apply_changes:
            transaction.set_rollback(True)
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "PREVIEW: no se guardó ningún archivo ni cambio en PostgreSQL."
                )
            )
        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Materialización finalizada."
                )
            )
