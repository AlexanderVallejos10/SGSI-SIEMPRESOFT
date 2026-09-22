from collections import OrderedDict
from pathlib import Path

from django.core.files import File
from django.db import transaction

from .models import (
    Context42Document,
    Context42DocumentKind,
    Context42DocumentVersion,
    InterestedPartyRow,
    LegalRequirementRow,
)
from .parser import (
    parse_interested_parties,
    parse_legal_requirements,
)


DEFAULT_DOCUMENTS = [
    {
        "slug":
            "partes-interesadas",
        "title":
            "Partes interesadas",
        "kind":
            Context42DocumentKind.INTERESTED,
        "sort_order":
            10,
        "description":
            (
                "Matriz de partes interesadas "
                "con necesidades y expectativas."
            ),
    },
    {
        "slug":
            "requisitos-legales",
        "title":
            (
                "Lista de requisitos legales, "
                "normativos y contractuales"
            ),
        "kind":
            Context42DocumentKind.LEGAL,
        "sort_order":
            20,
        "description":
            (
                "Listado vigente de requisitos "
                "legales, normativos y contractuales "
                "aplicables al SGSI."
            ),
    },
]


def ensure_documents():
    docs = []

    for payload in DEFAULT_DOCUMENTS:
        doc, _ = (
            Context42Document.objects
            .get_or_create(
                slug=payload[
                    "slug"
                ],
                defaults=payload,
            )
        )

        changed = False

        for key, value in payload.items():
            if (
                getattr(
                    doc,
                    key,
                )
                != value
            ):
                setattr(
                    doc,
                    key,
                    value,
                )
                changed = True

        if changed:
            doc.save(
                update_fields=[
                    "title",
                    "kind",
                    "sort_order",
                    "description",
                ]
            )

        docs.append(doc)

    return docs


def detect_version_label(
    file_name,
):
    cleaned = (
        file_name
        or ""
    ).upper()

    tokens = (
        cleaned
        .replace("-", " ")
        .replace("_", " ")
        .split()
    )

    for token in tokens:
        if (
            token.startswith("V")
            and any(
                ch.isdigit()
                for ch in token
            )
        ):
            return token

    return "NUEVA"


@transaction.atomic
def import_version_rows(
    version,
):
    InterestedPartyRow.objects.filter(
        version=version
    ).delete()

    LegalRequirementRow.objects.filter(
        version=version
    ).delete()

    path = version.file.path

    if (
        version.document.kind
        == Context42DocumentKind.INTERESTED
    ):
        rows = (
            parse_interested_parties(
                path
            )
        )

        InterestedPartyRow.objects.bulk_create(
            [
                InterestedPartyRow(
                    version=version,
                    **row,
                )
                for row in rows
            ]
        )

        return len(rows)

    if (
        version.document.kind
        == Context42DocumentKind.LEGAL
    ):
        rows = (
            parse_legal_requirements(
                path
            )
        )

        LegalRequirementRow.objects.bulk_create(
            [
                LegalRequirementRow(
                    version=version,
                    **row,
                )
                for row in rows
            ]
        )

        return len(rows)

    return 0


@transaction.atomic
def register_version(
    document,
    uploaded_file,
    actor=None,
    notes="",
    version_label="",
):
    if not version_label:
        version_label = (
            detect_version_label(
                getattr(
                    uploaded_file,
                    "name",
                    "",
                )
            )
        )

    Context42DocumentVersion.objects.filter(
        document=document,
        is_current=True,
    ).update(
        is_current=False
    )

    version = (
        Context42DocumentVersion.objects
        .create(
            document=document,
            file=uploaded_file,
            original_name=getattr(
                uploaded_file,
                "name",
                "archivo",
            ),
            version_label=(
                version_label
            ),
            notes=notes,
            is_current=True,
            created_by=(
                actor
                if getattr(
                    actor,
                    "is_authenticated",
                    False,
                )
                else None
            ),
            updated_by=(
                actor
                if getattr(
                    actor,
                    "is_authenticated",
                    False,
                )
                else None
            ),
        )
    )

    import_version_rows(
        version
    )

    return version


@transaction.atomic
def register_initial_file(
    *,
    document,
    file_path,
    version_label,
):
    if document.versions.exists():
        return (
            document.versions
            .filter(
                is_current=True
            )
            .first()
            or document.versions.first()
        )

    path = Path(
        file_path
    )

    with open(
        path,
        "rb",
    ) as handle:
        django_file = File(
            handle,
            name=path.name,
        )

        version = (
            Context42DocumentVersion.objects
            .create(
                document=document,
                file=django_file,
                original_name=path.name,
                version_label=version_label,
                is_current=True,
            )
        )

    import_version_rows(
        version
    )

    return version


def party_groups(
    version,
):
    groups = OrderedDict()

    if not version:
        return []

    rows = (
        version.party_rows
        .filter(
            is_active=True
        )
        .order_by(
            "source_row",
            "party_name",
        )
    )

    for row in rows:
        groups.setdefault(
            row.party_name,
            [],
        ).append(row)

    return [
        {
            "name":
                name,
            "rows":
                items,
        }
        for name, items
        in groups.items()
    ]


def legal_summary(
    version,
):
    if not version:
        return {
            "statuses": [],
            "responsibles": [],
            "promulgated": [],
            "count": 0,
        }

    rows = list(
        version.legal_rows
        .filter(
            is_active=True
        )
    )

    return {
        "statuses":
            sorted(
                {
                    row.status
                    for row in rows
                    if row.status
                }
            ),
        "responsibles":
            sorted(
                {
                    row.responsible
                    for row in rows
                    if row.responsible
                }
            ),
        "promulgated":
            sorted(
                {
                    row.promulgated_by
                    for row in rows
                    if row.promulgated_by
                }
            ),
        "count":
            len(rows),
    }
