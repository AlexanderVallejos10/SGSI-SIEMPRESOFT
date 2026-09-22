import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.organization.models import Position

from apps.processes.models import (
    ProcessCategory,
    ProcessCategoryKind,
    ProcessCategoryRelation,
    ProcessDocumentKind,
    ProcessNode,
    ProcessReferenceDocument,
    ProcessRelation,
    ProcessRelationType,
)
from apps.processes.services import register_reference_path


SCOPE_PDF = Path(
    "/app/imports/"
    "01 - Documento_sobre_el_alcance_del_SGSI_V0.13.pdf"
)

MAP_PDF = Path(
    "/app/imports/"
    "02 - MAPA DE PROCESOS SIEMPRESOFT_V0.14.pdf"
)


CATEGORY_DATA = [
    {
        "code": "PROC-STRAT",
        "name": "Procesos estratégicos",
        "kind": ProcessCategoryKind.STRATEGIC,
        "sort_order": 10,
        "color": "#d8eaf7",
    },
    {
        "code": "PROC-OPER",
        "name": "Procesos operativos",
        "kind": ProcessCategoryKind.OPERATIONAL,
        "sort_order": 20,
        "color": "#f8e3d7",
    },
    {
        "code": "PROC-SUP",
        "name": "Procesos de apoyo",
        "kind": ProcessCategoryKind.SUPPORT,
        "sort_order": 30,
        "color": "#e8f2d9",
    },
]


PROCESS_DATA = [
    ("PROC-RD", "Revisión por la Dirección", "strategic", 500, 74, False, "Gerente General", "Proceso estratégico de revisión y dirección del SGSI."),
    ("PROC-VENTAS", "Ventas", "operational", 105, 238, True, "Ventas", "Captación de nuevos clientes."),
    ("PROC-OSE", "Validación OSE", "operational", 505, 182, True, "Producción", "Validación de comprobantes electrónicos dentro del alcance del SGSI."),
    ("PROC-CONS", "Consultoría", "operational", 805, 238, True, "Consultoría", "Asesoramiento de inicio de operaciones con los servicios contratados."),
    ("PROC-SOPORTE", "Soporte al Cliente", "operational", 315, 338, True, "Help Desk", "Soporte y atención de primer nivel relacionado con los servicios."),
    ("PROC-DES", "Desarrollo", "operational", 535, 338, True, "Desarrollo", "Análisis, diseño y programación de código fuente del Sistema ERP y servicio OSE."),
    ("PROC-PROD", "Producción", "operational", 755, 338, True, "Producción", "Despliegue del Sistema ERP y servicio OSE."),
    ("PROC-RRHH", "Recursos Humanos", "support", 205, 542, True, "Administrativo", "Gestión de recursos humanos como proceso de apoyo."),
    ("PROC-FC", "Facturación y Cobranza", "support", 395, 542, True, "Administrativo", "Facturación y cobranza como proceso de apoyo."),
    ("PROC-LOG", "Logística", "support", 590, 542, True, "Administrativo", "Logística como proceso de apoyo."),
    ("PROC-INFRA", "Infraestructura Tecnológica", "support", 820, 542, True, "Plataforma", "Infraestructura tecnológica necesaria para la operación."),
    ("PROC-CONT", "Contabilidad", "support", 430, 625, False, "Administrativo", "Proceso de apoyo excluido del alcance del SGSI."),
    ("PROC-MKT", "Marketing", "support", 650, 625, False, "Ventas", "Gestión de publicidad y comunicación de servicios. Puede moverse a otra categoría."),
]


RELATIONS = [
    ("PROC-VENTAS", "PROC-CONS", "flow"),
    ("PROC-OSE", "PROC-SOPORTE", "flow"),
    ("PROC-SOPORTE", "PROC-DES", "flow"),
    ("PROC-DES", "PROC-PROD", "flow"),
    ("PROC-PROD", "PROC-DES", "flow"),
    ("PROC-SOPORTE", "PROC-PROD", "flow"),
]


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(ch)
    )
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value.casefold(),
    ).strip()


def find_position(text):
    needle = normalize(text)
    candidates = list(
        Position.objects
        .filter(is_active=True)
        .select_related("area")
        .order_by("title")
    )

    exact = next(
        (
            item
            for item in candidates
            if normalize(item.title) == needle
        ),
        None,
    )

    if exact:
        return exact

    return next(
        (
            item
            for item in candidates
            if needle in normalize(item.title)
            or normalize(item.title) in needle
        ),
        None,
    )


@transaction.atomic
def seed_map(apply_changes):
    categories = {}

    for payload in CATEGORY_DATA:
        category, _ = ProcessCategory.objects.get_or_create(
            kind=payload["kind"],
            defaults=payload,
        )
        categories[payload["kind"]] = category

    nodes = {}
    created_nodes = 0

    for (
        code,
        name,
        category_kind,
        x,
        y,
        scope,
        owner_like,
        description,
    ) in PROCESS_DATA:
        process = (
            ProcessNode.objects
            .filter(code=code)
            .first()
        )

        if process is None:
            process = ProcessNode.objects.create(
                code=code,
                name=name,
                category=categories[category_kind],
                x=x,
                y=y,
                is_in_scope=scope,
                description=description,
                owner_position=find_position(owner_like),
            )
            created_nodes += 1

        nodes[code] = process

    created_relations = 0

    for source_code, target_code, rel_type in RELATIONS:
        _, created = ProcessRelation.objects.get_or_create(
            source=nodes[source_code],
            target=nodes[target_code],
            relation_type=rel_type,
            defaults={"is_active": True},
        )

        if created:
            created_relations += 1

    ProcessCategoryRelation.objects.get_or_create(
        source=categories["strategic"],
        target=categories["operational"],
        relation_type=ProcessRelationType.GOVERNANCE,
        defaults={
            "label": "Dirección y revisión",
            "is_active": True,
        },
    )

    ProcessCategoryRelation.objects.get_or_create(
        source=categories["support"],
        target=categories["operational"],
        relation_type=ProcessRelationType.SUPPORT,
        defaults={
            "label": "Procesos de apoyo",
            "is_active": True,
        },
    )

    scope_doc, _ = ProcessReferenceDocument.objects.get_or_create(
        kind=ProcessDocumentKind.SCOPE,
        defaults={
            "slug": "alcance-sgsi",
            "title": "Documento sobre el alcance del SGSI",
            "description": (
                "Documento que define límites, procesos, "
                "servicios, unidades organizativas y exclusiones."
            ),
            "sort_order": 10,
        },
    )

    map_doc, _ = ProcessReferenceDocument.objects.get_or_create(
        kind=ProcessDocumentKind.MAP,
        defaults={
            "slug": "mapa-procesos",
            "title": "Mapa de procesos",
            "description": "Fuente documental oficial del mapa de procesos.",
            "sort_order": 20,
        },
    )

    register_reference_path(
        document=scope_doc,
        file_path=SCOPE_PDF,
        version_label="0.13",
        notes="Carga inicial del documento de alcance.",
    )

    register_reference_path(
        document=map_doc,
        file_path=MAP_PDF,
        version_label="0.14",
        notes="Carga inicial del mapa de procesos.",
    )

    if not apply_changes:
        transaction.set_rollback(True)

    return {
        "categories": len(categories),
        "nodes": len(nodes),
        "created_nodes": created_nodes,
        "created_relations": created_relations,
    }


class Command(BaseCommand):
    help = (
        "Carga la estructura inicial del mapa de procesos "
        "y los dos PDFs de referencia."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
        )

    def handle(self, *args, **options):
        if not SCOPE_PDF.is_file():
            raise CommandError(f"No existe: {SCOPE_PDF}")

        if not MAP_PDF.is_file():
            raise CommandError(f"No existe: {MAP_PDF}")

        result = seed_map(options["apply"])

        self.stdout.write(
            "=== MAPA DE PROCESOS SIEMPRESOFT ==="
        )
        self.stdout.write(
            "Modo: "
            + (
                "APPLY"
                if options["apply"]
                else "PREVIEW"
            )
        )
        self.stdout.write(
            f"Categorías: {result['categories']}"
        )
        self.stdout.write(
            f"Procesos: {result['nodes']}"
        )
        self.stdout.write(
            f"Procesos nuevos: {result['created_nodes']}"
        )
        self.stdout.write(
            f"Relaciones nuevas: {result['created_relations']}"
        )

        if not options["apply"]:
            self.stdout.write(
                "PREVIEW: no se modificó PostgreSQL."
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Mapa de procesos cargado."
                )
            )
