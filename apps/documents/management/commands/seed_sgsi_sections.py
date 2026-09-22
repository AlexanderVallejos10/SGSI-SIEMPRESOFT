from django.core.management.base import BaseCommand
from django.db import transaction

from apps.documents.models import SGSISection


MANUAL_VERSION = "0.7"


SECTIONS = [
    {
        "code": "1",
        "title": "Introducción e historia",
        "parent": None,
        "sort_order": 100,
    },
    {
        "code": "2",
        "title": "Objetivo, alcance y usuarios",
        "parent": None,
        "sort_order": 200,
    },
    {
        "code": "3",
        "title": "Marco de trabajo",
        "parent": None,
        "sort_order": 300,
    },
    {
        "code": "3.1",
        "title": "Políticas",
        "parent": "3",
        "sort_order": 310,
    },
    {
        "code": "3.2",
        "title": "Procedimientos",
        "parent": "3",
        "sort_order": 320,
    },
    {
        "code": "3.3",
        "title": "Estándares",
        "parent": "3",
        "sort_order": 330,
    },
    {
        "code": "3.4",
        "title": "Instructivos o Guías",
        "parent": "3",
        "sort_order": 340,
    },

    {
        "code": "4",
        "title": "Contexto de la organización",
        "parent": None,
        "sort_order": 400,
    },
    {
        "code": "4.1",
        "title": "Conocimiento de la organización y su contexto",
        "parent": "4",
        "sort_order": 410,
    },
    {
        "code": "4.2",
        "title": "Comprender las necesidades y expectativas de las partes interesadas",
        "parent": "4",
        "sort_order": 420,
    },
    {
        "code": "4.3",
        "title": "Alcance del SGSI",
        "parent": "4",
        "sort_order": 430,
    },
    {
        "code": "4.4",
        "title": "Sistema de Gestión de seguridad de la información",
        "parent": "4",
        "sort_order": 440,
    },

    {
        "code": "5",
        "title": "Liderazgo",
        "parent": None,
        "sort_order": 500,
    },
    {
        "code": "5.1",
        "title": "Liderazgo y compromiso",
        "parent": "5",
        "sort_order": 510,
    },
    {
        "code": "5.2",
        "title": "Política",
        "parent": "5",
        "sort_order": 520,
    },
    {
        "code": "5.3",
        "title": "Autoridades, roles y responsabilidades",
        "parent": "5",
        "sort_order": 530,
    },

    {
        "code": "6",
        "title": "Planificación",
        "parent": None,
        "sort_order": 600,
    },
    {
        "code": "6.1",
        "title": "Acciones para tratar los riesgos y oportunidades",
        "parent": "6",
        "sort_order": 610,
    },
    {
        "code": "6.2",
        "title": "Objetivos de seguridad de la información y el plan para lograrlos",
        "parent": "6",
        "sort_order": 620,
    },
    {
        "code": "6.3",
        "title": "Planificación de cambios",
        "parent": "6",
        "sort_order": 630,
    },

    {
        "code": "7",
        "title": "Apoyo",
        "parent": None,
        "sort_order": 700,
    },
    {
        "code": "7.1",
        "title": "Recursos",
        "parent": "7",
        "sort_order": 710,
    },
    {
        "code": "7.2",
        "title": "Competencia, consciencia y capacitación",
        "parent": "7",
        "sort_order": 720,
    },
    {
        "code": "7.3",
        "title": "Toma de conciencia",
        "parent": "7",
        "sort_order": 730,
    },
    {
        "code": "7.4",
        "title": "Comunicación",
        "parent": "7",
        "sort_order": 740,
    },
    {
        "code": "7.5",
        "title": "Información documentada",
        "parent": "7",
        "sort_order": 750,
    },

    {
        "code": "8",
        "title": "Operación",
        "parent": None,
        "sort_order": 800,
    },
    {
        "code": "8.1",
        "title": "Planeamiento y control operacional",
        "parent": "8",
        "sort_order": 810,
    },
    {
        "code": "8.2",
        "title": "Evaluación de riesgos de seguridad de información",
        "parent": "8",
        "sort_order": 820,
    },
    {
        "code": "8.3",
        "title": "Tratamiento de riesgos de seguridad de información",
        "parent": "8",
        "sort_order": 830,
    },

    {
        "code": "9",
        "title": "Evaluación del desempeño",
        "parent": None,
        "sort_order": 900,
    },
    {
        "code": "9.1",
        "title": "Monitoreo, medición, análisis y evaluación",
        "parent": "9",
        "sort_order": 910,
    },
    {
        "code": "9.2",
        "title": "Auditoría interna",
        "parent": "9",
        "sort_order": 920,
    },
    {
        "code": "9.3",
        "title": "Revisión de la Gerencia",
        "parent": "9",
        "sort_order": 930,
    },

    {
        "code": "10",
        "title": "Mejora",
        "parent": None,
        "sort_order": 1000,
    },
    {
        "code": "10.1",
        "title": "Mejora continua",
        "parent": "10",
        "sort_order": 1010,
    },
    {
        "code": "10.2",
        "title": "No conformidades y acciones correctivas",
        "parent": "10",
        "sort_order": 1020,
    },

    {
        "code": "11",
        "title": "Validez y gestión de documentos",
        "parent": None,
        "sort_order": 1100,
    },
]


@transaction.atomic
def sync_sections():
    results = {
        "created": 0,
        "updated": 0,
    }

    section_map = {}

    for item in SECTIONS:
        parent = None

        if item["parent"]:
            parent = section_map.get(
                item["parent"]
            )

            if parent is None:
                parent = SGSISection.objects.get(
                    code=item["parent"]
                )

        section, created = (
            SGSISection.objects.update_or_create(
                code=item["code"],
                defaults={
                    "title": item["title"],
                    "parent": parent,
                    "sort_order": item["sort_order"],
                    "manual_version": MANUAL_VERSION,
                    "is_active": True,
                },
            )
        )

        section_map[item["code"]] = section

        if created:
            results["created"] += 1
        else:
            results["updated"] += 1

    return results


class Command(BaseCommand):
    help = (
        "Crea o actualiza la estructura 1-11 "
        "del Manual del SGSI V0.7."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            "Sincronizando estructura del Manual SGSI..."
        )

        results = sync_sections()

        self.stdout.write(
            self.style.SUCCESS(
                "Estructura SGSI sincronizada."
            )
        )

        self.stdout.write(
            f"Secciones creadas: {results['created']}"
        )

        self.stdout.write(
            f"Secciones actualizadas: {results['updated']}"
        )

        self.stdout.write(
            f"Total esperado: {len(SECTIONS)}"
        )