import re
import unicodedata

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organization.models import (
    OrganizationRelationType,
    Position,
    PositionAssignment,
)


User = get_user_model()


REFERENCE_POSITIONS = [
    {
        "code": "ORG-GG",
        "title": "Gerente General",
        "parent": None,
        "order": 10,
        "color": "#fff3ca",
    },
    {
        "code": "ORG-GOP",
        "title": "Gerente de Operaciones",
        "parent": "ORG-GG",
        "order": 10,
        "color": "#e6f2ff",
    },
    {
        "code": "ORG-JCONS",
        "title": "Jefe de Consultoría",
        "parent": "ORG-GOP",
        "order": 10,
        "color": "#faeeee",
    },
    {
        "code": "ORG-CONS",
        "title": "Consultores",
        "parent": "ORG-JCONS",
        "order": 10,
        "color": "#ffffff",
        "max_occupants": 0,
    },
    {
        "code": "ORG-JHD",
        "title": "Jefe de Help Desk",
        "parent": "ORG-GOP",
        "order": 20,
        "color": "#fff6d9",
    },
    {
        "code": "ORG-AHD",
        "title": "Analistas Help Desk",
        "parent": "ORG-JHD",
        "order": 10,
        "color": "#ffffff",
        "max_occupants": 0,
    },
    {
        "code": "ORG-CSM",
        "title": "CSM / Administrador del Conocimiento",
        "parent": "ORG-GOP",
        "order": 30,
        "color": "#fff6a8",
    },
    {
        "code": "ORG-IID",
        "title": "Ingeniero de Investigación I+D",
        "parent": "ORG-GG",
        "order": 20,
        "color": "#f2ddf5",
    },
    {
        "code": "ORG-VENTAS",
        "title": "Responsable de Ventas y Marketing",
        "parent": "ORG-GG",
        "order": 30,
        "color": "#e2f5df",
    },
    {
        "code": "ORG-JDES",
        "title": "Jefe de Desarrollo",
        "parent": "ORG-GG",
        "order": 40,
        "color": "#ededed",
    },
    {
        "code": "ORG-DES",
        "title": "Desarrolladores",
        "parent": "ORG-JDES",
        "order": 10,
        "color": "#ffffff",
        "max_occupants": 0,
    },
    {
        "code": "ORG-JPROD",
        "title": "Jefe de Producción / Oficial de Seguridad de la Información",
        "parent": "ORG-GG",
        "order": 50,
        "color": "#f6dede",
    },
    {
        "code": "ORG-APROD",
        "title": "Asistente de Producción",
        "parent": "ORG-JPROD",
        "order": 10,
        "color": "#ffffff",
    },
    {
        "code": "ORG-PLAT",
        "title": "Ingeniero de Plataforma",
        "parent": "ORG-APROD",
        "order": 10,
        "color": "#ffffff",
    },
    {
        "code": "ORG-JQA",
        "title": "Jefe de Control de Calidad",
        "parent": "ORG-GG",
        "order": 60,
        "color": "#def4e4",
    },
    {
        "code": "ORG-QA",
        "title": "Analista QA",
        "parent": "ORG-JQA",
        "order": 10,
        "color": "#ffffff",
    },
    {
        "code": "ORG-JSUP",
        "title": "Jefe de Ingeniería de Soporte",
        "parent": "ORG-GG",
        "order": 70,
        "color": "#e8dcf5",
    },
    {
        "code": "ORG-ISUP",
        "title": "Ingenieros de Soporte",
        "parent": "ORG-JSUP",
        "order": 10,
        "color": "#ffffff",
        "max_occupants": 0,
    },
    {
        "code": "ORG-AADM",
        "title": "Asistente Administrativo",
        "parent": "ORG-GG",
        "order": 80,
        "color": "#e9e9e9",
    },
    {
        "code": "ORG-SST",
        "title": "Responsable de SST",
        "parent": "ORG-GG",
        "order": 90,
        "color": "#d9d9d9",
        "relation": OrganizationRelationType.STAFF,
    },
    {
        "code": "ORG-COM-SST",
        "title": "Comité de SST",
        "parent": "ORG-SST",
        "order": 10,
        "color": "#ffffff",
        "relation": OrganizationRelationType.COMMITTEE,
        "max_occupants": 0,
    },
]


def normalize(value):
    value = unicodedata.normalize(
        "NFKD",
        str(value or ""),
    )
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


@transaction.atomic
def seed(apply_changes):
    position_map = {}

    for item in REFERENCE_POSITIONS:
        position, _ = Position.objects.update_or_create(
            code=item["code"],
            defaults={
                "title": item["title"],
                "relation_type": item.get(
                    "relation",
                    OrganizationRelationType.LINE,
                ),
                "sort_order": item["order"],
                "max_occupants": item.get(
                    "max_occupants",
                    1,
                ),
                "is_active": True,
                "color": item["color"],
            },
        )

        position_map[item["code"]] = position

    for item in REFERENCE_POSITIONS:
        parent_code = item["parent"]

        if not parent_code:
            continue

        position = position_map[
            item["code"]
        ]

        parent = position_map[
            parent_code
        ]

        if position.parent_id != parent.id:
            position.parent = parent
            position.save(
                update_fields=(
                    "parent",
                    "updated_at",
                )
            )

    by_title = {
        normalize(position.title): position
        for position in Position.objects.filter(
            is_active=True
        )
    }

    root = position_map[
        "ORG-GG"
    ]

    users = User.objects.all().order_by(
        "username"
    )

    created_extra = 0
    assigned = 0

    for index, user in enumerate(
        users,
        start=1,
    ):
        title = getattr(
            user,
            "position",
            "",
        )

        if not title:
            continue

        position = by_title.get(
            normalize(title)
        )

        if position is None:
            code = (
                f"ORG-REAL-{index:03d}"
            )

            position, created = (
                Position.objects
                .get_or_create(
                    code=code,
                    defaults={
                        "title": title,
                        "parent": root,
                        "sort_order": 500 + index,
                        "max_occupants": 1,
                        "is_active": True,
                        "color": "#f0f3f6",
                    },
                )
            )

            if created:
                created_extra += 1

            by_title[
                normalize(title)
            ] = position

        active = (
            PositionAssignment.objects
            .filter(
                user=user,
                end_date__isnull=True,
                is_primary=True,
            )
            .first()
        )

        if active is None:
            PositionAssignment.objects.create(
                position=position,
                user=user,
                is_primary=True,
            )
            assigned += 1

    if not apply_changes:
        transaction.set_rollback(
            True
        )

    return (
        len(position_map),
        created_extra,
        assigned,
    )


class Command(BaseCommand):
    help = (
        "Carga la estructura inicial del organigrama "
        "tomando como referencia el organigrama de SIEMPRESOFT "
        "y asigna usuarios por coincidencia exacta de cargo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Guarda los cambios.",
        )

    def handle(self, *args, **options):
        apply_changes = options[
            "apply"
        ]

        reference, extras, assigned = seed(
            apply_changes
        )

        self.stdout.write(
            "=== ORGANIGRAMA SIEMPRESOFT ==="
        )
        self.stdout.write(
            f"Modo: {'APPLY' if apply_changes else 'PREVIEW'}"
        )
        self.stdout.write(
            f"Puestos de referencia: {reference}"
        )
        self.stdout.write(
            f"Puestos adicionales desde usuarios: {extras}"
        )
        self.stdout.write(
            f"Usuarios asignados: {assigned}"
        )

        if not apply_changes:
            self.stdout.write(
                "PREVIEW: transacción revertida."
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Organigrama cargado."
                )
            )
