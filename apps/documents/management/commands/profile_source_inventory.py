import os
import re
import unicodedata
from collections import Counter

from django.core.management.base import BaseCommand

from apps.documents.models import SourceArtifact, SourcePackage


def normalize_text(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(
        ch for ch in value if not unicodedata.combining(ch)
    )
    return value.casefold()


def first_folder(path):
    parts = [p for p in (path or "").replace("\\", "/").split("/") if p]
    return parts[0] if parts else "(sin carpeta)"


def lifecycle_hint(path):
    text = normalize_text(path)

    if any(
        token in text
        for token in (
            "no vigente",
            "no vigentes",
            "obsoleto",
            "obsoletos",
            "deprecated",
        )
    ):
        return "no_vigente"

    if any(
        token in text
        for token in (
            "borrador",
            "draft",
        )
    ):
        return "borrador"

    if any(
        token in text
        for token in (
            "documentos vigentes",
            "/vigentes/",
            " vigente",
        )
    ):
        return "vigente"

    if any(
        token in text
        for token in (
            "historico",
            "historica",
            "historial",
            "archivo historico",
        )
    ):
        return "historico"

    return "sin_clasificar"


def family_hint(name, path, extension):
    text = normalize_text(f"{name} {path}")
    ext = normalize_text(extension)

    rules = (
        ("politica", ("politica",)),
        ("manual", ("manual",)),
        ("procedimiento", ("procedimiento",)),
        ("instructivo", ("instructivo",)),
        ("guia", ("guia",)),
        ("estandar", ("estandar",)),
        ("matriz", ("matriz",)),
        ("dashboard", ("dashboard", "tablero")),
        ("formato", ("formato", "formulario")),
        ("plantilla", ("plantilla", "template")),
        ("registro", ("registro",)),
        ("acta", ("acta",)),
        ("informe", ("informe",)),
        ("reporte", ("reporte",)),
        ("evidencia", ("evidencia",)),
    )

    for label, tokens in rules:
        if any(token in text for token in tokens):
            return label

    if ext in {"xlsx", "xls", "xlsm", "csv", "ods"}:
        return "hoja_calculo"

    if ext in {"pdf"}:
        return "pdf_otro"

    if ext in {"doc", "docx", "odt"}:
        return "documento_texto_otro"

    if ext in {
        "png", "jpg", "jpeg", "gif", "bmp",
        "tif", "tiff", "webp", "svg",
    }:
        return "imagen"

    if ext in {"ppt", "pptx", "odp"}:
        return "presentacion"

    if ext in {"zip", "rar", "7z", "tar", "gz"}:
        return "archivo_comprimido"

    return "otro"


class Command(BaseCommand):
    help = (
        "Genera un perfil del inventario documental real, "
        "sin modificar datos, para diseñar la clasificación "
        "y migración SGSI sobre el corpus existente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--top",
            type=int,
            default=30,
            help="Cantidad máxima de valores a mostrar por bloque.",
        )

    def handle(self, *args, **options):
        top = options["top"]

        packages = SourcePackage.objects.all()
        artifacts = SourceArtifact.objects.all()
        canonical = artifacts.filter(duplicate_of__isnull=True)

        self.stdout.write("=== PERFIL DEL CORPUS SGSI ===")
        self.stdout.write(
            f"Paquetes registrados: {packages.count()}"
        )
        self.stdout.write(
            f"Ocurrencias de archivo: {artifacts.count()}"
        )
        self.stdout.write(
            f"Contenidos canónicos: {canonical.count()}"
        )
        self.stdout.write(
            "Ocurrencias duplicadas: "
            f"{artifacts.filter(duplicate_of__isnull=False).count()}"
        )
        self.stdout.write("")

        package_status = Counter(
            packages.values_list("status", flat=True)
        )
        self.stdout.write("=== PAQUETES POR ESTADO ===")
        for key, value in package_status.most_common():
            self.stdout.write(f"{key}: {value}")
        self.stdout.write("")

        quality_status = Counter(
            artifacts.values_list("quality_status", flat=True)
        )
        self.stdout.write("=== ARCHIVOS POR CALIDAD ===")
        for key, value in quality_status.most_common():
            self.stdout.write(f"{key}: {value}")
        self.stdout.write("")

        extensions = Counter(
            (
                (ext or "(sin extension)").lower()
                for ext in canonical.values_list(
                    "extension",
                    flat=True,
                )
            )
        )
        self.stdout.write(
            "=== EXTENSIONES - CONTENIDO CANONICO ==="
        )
        for key, value in extensions.most_common(top):
            self.stdout.write(f"{key}: {value}")
        self.stdout.write("")

        roots = Counter()
        lifecycles = Counter()
        families = Counter()

        dashboard_candidates = []
        sgsi_candidates = []

        seen_dashboard = set()
        seen_sgsi = set()

        sgsi_tokens = (
            "sgsi",
            "seguridad de la informacion",
            "iso 27001",
            "iso27001",
            "riesgo",
            "auditoria",
            "control",
            "activo",
            "incidente",
            "vulnerabilidad",
            "continuidad",
            "parte interesada",
            "requisito legal",
            "alcance",
            "foda",
            "organigrama",
            "objetivo",
        )

        for item in canonical.iterator(chunk_size=1000):
            roots[first_folder(item.original_path)] += 1

            lifecycles[
                lifecycle_hint(item.original_path)
            ] += 1

            families[
                family_hint(
                    item.original_name,
                    item.original_path,
                    item.extension,
                )
            ] += 1

            normalized = normalize_text(
                f"{item.original_name} {item.original_path}"
            )

            if (
                any(
                    token in normalized
                    for token in (
                        "dashboard",
                        "tablero",
                        "rendimiento sgsi",
                        "verificacionnorma",
                        "verificacion norma",
                    )
                )
                and item.checksum_sha256 not in seen_dashboard
            ):
                seen_dashboard.add(item.checksum_sha256)
                dashboard_candidates.append(
                    (
                        item.original_name,
                        item.original_path,
                        item.extension,
                    )
                )

            if (
                any(token in normalized for token in sgsi_tokens)
                and item.checksum_sha256 not in seen_sgsi
            ):
                seen_sgsi.add(item.checksum_sha256)
                sgsi_candidates.append(
                    (
                        item.original_name,
                        item.original_path,
                        item.extension,
                    )
                )

        self.stdout.write(
            "=== CARPETAS RAIZ - CONTENIDO CANONICO ==="
        )
        for key, value in roots.most_common(top):
            self.stdout.write(f"{value:>6} | {key}")
        self.stdout.write("")

        self.stdout.write(
            "=== INDICIOS DE CICLO DE VIDA ==="
        )
        for key, value in lifecycles.most_common():
            self.stdout.write(f"{key}: {value}")
        self.stdout.write("")

        self.stdout.write(
            "=== FAMILIAS DOCUMENTALES ESTIMADAS ==="
        )
        for key, value in families.most_common():
            self.stdout.write(f"{key}: {value}")
        self.stdout.write("")

        self.stdout.write(
            "=== CANDIDATOS DASHBOARD / VERIFICACION ==="
        )
        if dashboard_candidates:
            for name, path, ext in dashboard_candidates[:top]:
                self.stdout.write(
                    f"{ext or '-':<6} | {name} | {path}"
                )
        else:
            self.stdout.write("(sin coincidencias)")
        self.stdout.write("")

        self.stdout.write(
            "=== MUESTRA DE CANDIDATOS SGSI ==="
        )
        if sgsi_candidates:
            for name, path, ext in sgsi_candidates[:top]:
                self.stdout.write(
                    f"{ext or '-':<6} | {name} | {path}"
                )
        else:
            self.stdout.write("(sin coincidencias)")

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Perfil generado sin modificar la base de datos."
            )
        )
