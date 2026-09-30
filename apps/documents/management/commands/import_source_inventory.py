import hashlib
import mimetypes
import os
import unicodedata
import zipfile
from datetime import datetime
from pathlib import PurePosixPath

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.documents.models import (
    SourceArtifact,
    SourceArtifactKind,
    SourcePackage,
    SourcePackageStatus,
    SourceQualityStatus,
)


CHUNK_SIZE = 1024 * 1024


def normalize_member_path(value):
    """Normaliza la ruta lógica sin alterar su significado documental."""
    value = value.replace("\\", "/").lstrip("/")
    return unicodedata.normalize("NFC", value)


# Material criptográfico y credenciales: nunca se guarda en el sistema documental.
SECRET_EXTENSIONS = {
    "p12", "pfx", "pem", "key", "ppk", "jks", "keystore", "kdbx", "ovpn", "rdp",
}
# Documentos que la empresa usa para anotar claves: se omiten aunque sean Excel o Word.
# Su información útil (qué cuenta cambió de clave y cuándo) va al registro «Registro de cambio de claves».
SECRET_DOCUMENT_HINTS = ("registro de cambio de claves", "log gestion de claves")
DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "xlsm", "odt", "md", "mp4"}
SECRET_NAME_HINTS = (
    "bitlocker", "clave de recuperacion", "claves de recuperacion", "recovery key",
    "claves ssh", "id_rsa", "id_ed25519", "_key.zip", "credencial", "contrasena", "password",
    "certificados smime", "certificadossl", "certificado ssl", "wildcard", "siempresoft_ca",
)


def secret_reason(value):
    """Devuelve el motivo si la ruta es una llave, certificado privado o clave; si no, cadena vacía."""
    path = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    extension = PurePosixPath(path).suffix.lstrip(".")
    if extension in SECRET_EXTENSIONS:
        return f"archivo de llave o certificado privado (.{extension})"
    for hint in SECRET_DOCUMENT_HINTS:
        if hint in path:
            return f"documento con claves escritas ({hint})"
    if extension in DOCUMENT_EXTENSIONS:
        return ""  # un instructivo sobre BitLocker o certificados es un documento, no un secreto
    for hint in SECRET_NAME_HINTS:
        if hint in path:
            return f"ruta de credenciales ({hint})"
    # Dentro de carpetas restringidas o de certificados, lo que no es un documento
    # (zip de certificados, .cer, scripts, claves en .txt) no entra al sistema.
    folders = path.rsplit("/", 1)[0]
    if "restringida" in folders or "certificad" in folders or "/vpn" in folders:
        return f"archivo técnico en carpeta restringida (.{extension or 'sin extensión'})"
    return ""


def path_is_suspicious(value):
    parts = PurePosixPath(value).parts
    return any(part == ".." for part in parts)


def build_artifact_code(archive_name, original_path):
    seed = f"{archive_name}\n{original_path}".encode(
        "utf-8",
        errors="surrogatepass",
    )
    digest = hashlib.sha256(seed).hexdigest()
    return f"SRC-{digest[:20].upper()}"


def build_package_code(archive_name, checksum):
    seed = f"{archive_name}\n{checksum}".encode(
        "utf-8",
        errors="surrogatepass",
    )
    digest = hashlib.sha256(seed).hexdigest()
    return f"PKG-{digest[:20].upper()}"


def calculate_file_sha256(file_path):
    digest = hashlib.sha256()

    with open(file_path, "rb") as source:
        while True:
            chunk = source.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def calculate_member_sha256(zip_file, zip_info):
    digest = hashlib.sha256()

    with zip_file.open(zip_info, "r") as source:
        while True:
            chunk = source.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def calculate_manifest_sha256(member_records):
    """
    Calcula un hash del contenido lógico del ZIP.

    El manifiesto depende únicamente de:
      - ruta normalizada del archivo interno
      - SHA-256 del contenido del archivo

    No depende de compresión, timestamps del ZIP ni orden físico de entradas.
    """
    digest = hashlib.sha256()

    ordered = sorted(
        member_records,
        key=lambda item: item["original_path"],
    )

    for item in ordered:
        line = (
            f"{item['original_path']}\0"
            f"{item['checksum_sha256']}\n"
        ).encode(
            "utf-8",
            errors="surrogatepass",
        )
        digest.update(line)

    return digest.hexdigest()


def member_modified_at(zip_info):
    try:
        value = datetime(*zip_info.date_time)
    except (TypeError, ValueError):
        return None

    if timezone.is_naive(value):
        value = timezone.make_aware(
            value,
            timezone.get_current_timezone(),
        )

    return value


def human_size(value):
    size = float(value)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024


class Command(BaseCommand):
    help = (
        "Inventaría un ZIP como SourcePackage y sus archivos "
        "como SourceArtifact, calculando SHA-256 binario y "
        "SHA-256 de manifiesto para detectar paquetes con "
        "contenido documental duplicado, preservando un canónico estable."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "zip_path",
            help=(
                "Ruta del ZIP dentro del contenedor. "
                "Ejemplo: /app/imports/archivo.zip"
            ),
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Ejecuta todas las validaciones y operaciones "
                "y revierte la transacción al finalizar."
            ),
        )

        parser.add_argument(
            "--show-files",
            action="store_true",
            help="Muestra una línea por cada archivo procesado.",
        )

        parser.add_argument(
            "--max-uncompressed-mb",
            type=int,
            default=2048,
            help=(
                "Límite de seguridad para el tamaño total "
                "descomprimido del ZIP. Por defecto: 2048 MB."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        zip_path = os.path.abspath(options["zip_path"])
        dry_run = options["dry_run"]
        show_files = options["show_files"]
        max_uncompressed_mb = options["max_uncompressed_mb"]

        if not os.path.isfile(zip_path):
            raise CommandError(
                f"No existe el archivo ZIP: {zip_path}"
            )

        if not zipfile.is_zipfile(zip_path):
            raise CommandError(
                f"El archivo no es un ZIP válido: {zip_path}"
            )

        archive_name = os.path.basename(zip_path)
        archive_size = os.path.getsize(zip_path)
        archive_checksum = calculate_file_sha256(zip_path)
        package_code = build_package_code(
            archive_name,
            archive_checksum,
        )

        summary = {
            "members": 0,
            "files": 0,
            "directories": 0,
            "created": 0,
            "updated": 0,
            "duplicates": 0,
            "invalid": 0,
            "bytes": 0,
            "secrets": [],
            "onedrive_errors": 0,
        }

        member_records = []

        self.stdout.write(
            f"Inventariando ZIP: {archive_name}"
        )

        # ----------------------------------------------------
        # Primera pasada: validar ZIP y calcular hashes internos.
        # Esto permite calcular el manifiesto antes de crear el
        # SourcePackage.
        # ----------------------------------------------------
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            entries = zip_file.infolist()
            summary["members"] = len(entries)

            total_uncompressed = sum(
                item.file_size
                for item in entries
                if not item.is_dir()
            )

            limit_bytes = max_uncompressed_mb * 1024 * 1024

            if total_uncompressed > limit_bytes:
                raise CommandError(
                    "El ZIP supera el límite de seguridad "
                    "de tamaño descomprimido: "
                    f"{human_size(total_uncompressed)} > "
                    f"{max_uncompressed_mb} MB"
                )

            for zip_info in entries:
                if zip_info.is_dir():
                    summary["directories"] += 1
                    continue

                original_path = normalize_member_path(
                    zip_info.filename
                )

                # Avisos de OneDrive sobre archivos que no se descargaron: no son documentos.
                if original_path.endswith("_Error.txt"):
                    summary["onedrive_errors"] += 1
                    continue

                # Llaves, certificados privados y claves: no se leen ni se guardan.
                reason = secret_reason(original_path)
                if reason:
                    summary["secrets"].append((original_path, reason))
                    continue

                original_name = PurePosixPath(
                    original_path
                ).name
                extension = PurePosixPath(
                    original_name
                ).suffix.lower().lstrip(".")
                mime_type = (
                    mimetypes.guess_type(original_name)[0]
                    or "application/octet-stream"
                )
                checksum = calculate_member_sha256(
                    zip_file,
                    zip_info,
                )

                member_records.append(
                    {
                        "zip_info": zip_info,
                        "original_path": original_path,
                        "original_name": original_name,
                        "extension": extension,
                        "mime_type": mime_type,
                        "checksum_sha256": checksum,
                        "suspicious": path_is_suspicious(
                            original_path
                        ),
                    }
                )

        summary["files"] = len(member_records)
        summary["bytes"] = sum(
            item["zip_info"].file_size
            for item in member_records
        )

        manifest_checksum = calculate_manifest_sha256(
            member_records
        )

        existing_package = (
            SourcePackage.objects
            .filter(code=package_code)
            .first()
        )

        # Solo un paquete CANÓNICO puede ser objetivo de duplicate_of.
        # Esto evita invertir la relación cuando se reprocesa el paquete
        # original después de uno de sus duplicados y previene ciclos A↔B.
        canonical_packages = (
            SourcePackage.objects
            .filter(duplicate_of__isnull=True)
            .exclude(code=package_code)
        )

        same_binary_package = (
            canonical_packages
            .filter(checksum_sha256=archive_checksum)
            .exclude(checksum_sha256="")
            .order_by("created_at", "code")
            .first()
        )

        same_manifest_package = (
            canonical_packages
            .filter(manifest_sha256=manifest_checksum)
            .exclude(manifest_sha256="")
            .order_by("created_at", "code")
            .first()
        )

        # Si el paquete ya existe como canónico, nunca se degrada por el
        # simple hecho de que exista una copia posterior con el mismo
        # manifiesto. Si ya era duplicado, se vuelve a resolver contra el
        # canónico disponible.
        if (
            existing_package is not None
            and existing_package.duplicate_of_id is None
        ):
            duplicate_package = None
        else:
            duplicate_package = (
                same_binary_package
                or same_manifest_package
            )

        if duplicate_package is not None:
            package_status = SourcePackageStatus.DUPLICATE

            if same_binary_package is not None:
                package_notes = (
                    "Paquete binariamente idéntico a "
                    f"{duplicate_package.code}."
                )
            else:
                package_notes = (
                    "Contenido documental idéntico a "
                    f"{duplicate_package.code}; el ZIP físico "
                    "es diferente, pero su manifiesto coincide."
                )

        elif (
            existing_package is not None
            and existing_package.status in {
                SourcePackageStatus.VERIFIED,
                SourcePackageStatus.WARNING,
            }
        ):
            package_status = existing_package.status
            package_notes = existing_package.notes

        else:
            package_status = SourcePackageStatus.PENDING
            package_notes = ""

        source_package, package_created = (
            SourcePackage.objects.update_or_create(
                code=package_code,
                defaults={
                    "original_name": archive_name,
                    "original_path": zip_path,
                    "size_bytes": archive_size,
                    "checksum_sha256": archive_checksum,
                    "manifest_sha256": manifest_checksum,
                    "duplicate_of": duplicate_package,
                    "status": package_status,
                    "notes": package_notes,
                },
            )
        )

        self.stdout.write(
            "PAQUETE | "
            f"{'CREADO' if package_created else 'ACTUALIZADO'} | "
            f"{source_package.code} | "
            f"{human_size(archive_size)} | "
            f"SHA256 {archive_checksum} | "
            f"MANIFEST {manifest_checksum} | "
            f"{source_package.status}"
        )

        if source_package.duplicate_of_id:
            self.stdout.write(
                "PAQUETE DUPLICADO DE | "
                f"{source_package.duplicate_of.code} | "
                f"{source_package.duplicate_of.original_name}"
            )

        # ----------------------------------------------------
        # Segunda pasada lógica: crear/actualizar SourceArtifact
        # usando los hashes calculados en la primera pasada.
        # ----------------------------------------------------
        for record in member_records:
            zip_info = record["zip_info"]
            original_path = record["original_path"]
            checksum = record["checksum_sha256"]
            artifact_code = build_artifact_code(
                archive_name,
                original_path,
            )

            existing = (
                SourceArtifact.objects
                .filter(code=artifact_code)
                .first()
            )

            canonical = (
                SourceArtifact.objects
                .filter(
                    checksum_sha256=checksum,
                    duplicate_of__isnull=True,
                )
                .order_by("created_at", "code")
                .first()
            )

            if record["suspicious"]:
                quality_status = SourceQualityStatus.INVALID
                quality_notes = (
                    "Ruta ZIP potencialmente insegura; "
                    "el archivo fue inventariado pero no "
                    "debe extraerse automáticamente."
                )
                duplicate_of = None
                summary["invalid"] += 1

            elif (
                canonical is not None
                and canonical.code != artifact_code
            ):
                quality_status = SourceQualityStatus.DUPLICATE
                quality_notes = (
                    "Contenido idéntico a "
                    f"{canonical.code}."
                )
                duplicate_of = canonical
                summary["duplicates"] += 1

            elif (
                existing is not None
                and existing.checksum_sha256 == checksum
                and existing.quality_status in {
                    SourceQualityStatus.VERIFIED,
                    SourceQualityStatus.WARNING,
                }
            ):
                quality_status = existing.quality_status
                quality_notes = existing.quality_notes
                duplicate_of = existing.duplicate_of

            else:
                quality_status = SourceQualityStatus.PENDING
                quality_notes = ""
                duplicate_of = None

            defaults = {
                "original_name": record["original_name"],
                "original_path": original_path,
                "source_archive": archive_name,
                "source_package": source_package,
                "source_kind": SourceArtifactKind.ZIP_MEMBER,
                "extension": record["extension"],
                "mime_type": record["mime_type"],
                "size_bytes": zip_info.file_size,
                "checksum_sha256": checksum,
                "source_modified_at": member_modified_at(zip_info),
                "source_verified": True,
                "quality_status": quality_status,
                "quality_notes": quality_notes,
                "duplicate_of": duplicate_of,
            }

            artifact, created = (
                SourceArtifact.objects.update_or_create(
                    code=artifact_code,
                    defaults=defaults,
                )
            )

            if created:
                summary["created"] += 1
                operation = "CREADO"
            else:
                summary["updated"] += 1
                operation = "ACTUALIZADO"

            if show_files:
                self.stdout.write(
                    f"{operation} | "
                    f"{artifact.code} | "
                    f"{artifact.original_path} | "
                    f"{human_size(artifact.size_bytes or 0)} | "
                    f"{artifact.quality_status} | "
                    f"paquete={source_package.code}"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Inventario del ZIP procesado correctamente."
            )
        )
        self.stdout.write(
            f"Paquete: {source_package.code}"
        )
        self.stdout.write(
            f"SHA-256 ZIP: {archive_checksum}"
        )
        self.stdout.write(
            f"Manifest SHA-256: {manifest_checksum}"
        )
        self.stdout.write(
            "Duplicado de: "
            + (
                source_package.duplicate_of.code
                if source_package.duplicate_of_id
                else "NO"
            )
        )
        self.stdout.write(
            f"Miembros ZIP: {summary['members']}"
        )
        self.stdout.write(
            f"Archivos: {summary['files']}"
        )
        self.stdout.write(
            f"Directorios omitidos: {summary['directories']}"
        )
        self.stdout.write(
            f"Creados: {summary['created']}"
        )
        self.stdout.write(
            f"Actualizados: {summary['updated']}"
        )
        self.stdout.write(
            f"Duplicados detectados: {summary['duplicates']}"
        )
        self.stdout.write(
            f"Inválidos: {summary['invalid']}"
        )
        self.stdout.write(
            f"Tamaño descomprimido: {human_size(summary['bytes'])}"
        )
        if summary["onedrive_errors"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Archivos que OneDrive no descargó (se omiten sus avisos _Error.txt): {summary['onedrive_errors']}"
                )
            )
        if summary["secrets"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    f"OMITIDOS POR SEGURIDAD: {len(summary['secrets'])} archivos con llaves, "
                    "certificados privados o claves. No se guardaron en el sistema; "
                    "deben custodiarse en un almacén de secretos."
                )
            )
            for path, reason in summary["secrets"][:40]:
                self.stdout.write(f"  - {path} | {reason}")
            if len(summary["secrets"]) > 40:
                self.stdout.write(f"  … y {len(summary['secrets']) - 40} más")

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN: la transacción fue revertida; "
                    "no se guardó ningún SourcePackage ni "
                    "SourceArtifact."
                )
            )
