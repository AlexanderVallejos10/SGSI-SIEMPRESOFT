from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.context41.models import (
    ContextDocument,
    ContextDocumentKind,
)
from apps.context41.services import (
    ensure_source_artifact_from_path,
    register_version,
)


SOURCES = [
    {
        "slug": "mision-vision-foda",
        "kind": ContextDocumentKind.MISSION_FODA,
        "title": "Misión y Visión – FODA",
        "description": (
            "Documento corporativo con la misión, visión "
            "y matriz de evaluación FODA."
        ),
        "sort_order": 10,
        "path": "/app/imports/01 - Misión y Visión - FODA.pdf",
        "version": "SIN-VERSION",
        "source_location": (
            "Repositorio de documentos online de Siempresoft/"
            "01 - Siempresoft/Uso Interno/Documentos vigentes/"
            "01 - Misión y Visión - FODA.pdf"
        ),
    },
    {
        "slug": "organigrama",
        "kind": ContextDocumentKind.ORGANIZATION,
        "title": "Organigrama",
        "description": (
            "Estructura organizacional vigente, mostrada "
            "también mediante el organigrama interactivo."
        ),
        "sort_order": 20,
        "path": "/app/imports/ORGANIGRAMA V. 21.pdf",
        "version": "21",
        "source_location": (
            "Repositorio de documentos online de Siempresoft/"
            "07 - Área de Administración/01 - Recursos Humanos/"
            "Uso interno/Documentos vigentes/Organigrama.pdf"
        ),
    },
    {
        "slug": "requisitos-legales",
        "kind": ContextDocumentKind.LEGAL,
        "title": (
            "Lista de requisitos legales, normativos, "
            "contractuales y de otra índole"
        ),
        "description": (
            "Registro estructurado de requisitos legales, "
            "regulatorios, contractuales y normativos."
        ),
        "sort_order": 30,
        "path": (
            "/app/imports/"
            "03 - Lista_de_requisitos_legales_"
            "normativos_contractuales_V0.15.xlsm"
        ),
        "version": "0.15",
        "source_location": (
            "Repositorio de documentos online de Siempresoft/"
            "01 - Siempresoft/Uso Interno/Documentos vigentes/"
            "03 - Lista de requisitos legales normativos "
            "contractuales.xlsx"
        ),
    },
]


@transaction.atomic
def run_seed(apply_changes, actor=None):
    result = []

    for item in SOURCES:
        path = Path(item["path"])

        if not path.is_file():
            raise CommandError(
                f"No existe la fuente: {path}"
            )

        document, _ = ContextDocument.objects.update_or_create(
            kind=item["kind"],
            defaults={
                "slug": item["slug"],
                "title": item["title"],
                "description": item["description"],
                "source_location": item["source_location"],
                "sort_order": item["sort_order"],
                "is_active": True,
            },
        )

        artifact = ensure_source_artifact_from_path(
            path
        )

        version = register_version(
            document=document,
            artifact=artifact,
            version_label=item["version"],
            notes="Carga inicial del numeral 4.1.",
            actor=actor,
        )

        legal_count = (
            version.legal_requirements.count()
            if item["kind"] == ContextDocumentKind.LEGAL
            else 0
        )

        result.append(
            {
                "document": document,
                "version": version,
                "legal_count": legal_count,
            }
        )

    if not apply_changes:
        transaction.set_rollback(True)

    return result


class Command(BaseCommand):
    help = (
        "Carga las tres fuentes vigentes del numeral 4.1: "
        "Misión/Visión/FODA, Organigrama y Lista legal."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
        )

    def handle(self, *args, **options):
        rows = run_seed(
            options["apply"]
        )

        self.stdout.write(
            "=== CONTEXTO SGSI 4.1 ==="
        )
        self.stdout.write(
            f"Modo: "
            f"{'APPLY' if options['apply'] else 'PREVIEW'}"
        )

        for row in rows:
            self.stdout.write(
                (
                    f"{row['document'].title} | "
                    f"versión={row['version'].version_label} | "
                    f"legal_rows={row['legal_count']}"
                )
            )

        if not options["apply"]:
            self.stdout.write(
                "PREVIEW: no se modificó PostgreSQL."
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Fuentes del numeral 4.1 cargadas."
                )
            )
