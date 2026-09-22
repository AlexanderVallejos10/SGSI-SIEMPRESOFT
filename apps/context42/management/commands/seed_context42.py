from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from apps.context42.services import (
    ensure_documents,
    register_initial_file,
)
from apps.context42.parser import (
    parse_interested_parties,
    parse_legal_requirements,
)


PARTIES = Path(
    "/app/imports/"
    "07 - Partes Interesadas_V0.4.xlsx"
)

LEGAL = Path(
    "/app/imports/"
    "03 - Lista_de_requisitos_legales_"
    "normativos_contractuales_V0.15.xlsm"
)


class Command(
    BaseCommand
):
    help = (
        "Carga los dos Excel reales "
        "que sustentan el numeral 4.2."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--apply",
            action="store_true",
        )

    def handle(
        self,
        *args,
        **options,
    ):
        if not PARTIES.is_file():
            raise CommandError(
                f"No existe: {PARTIES}"
            )

        if not LEGAL.is_file():
            raise CommandError(
                f"No existe: {LEGAL}"
            )

        party_rows = (
            parse_interested_parties(
                PARTIES
            )
        )

        legal_rows = (
            parse_legal_requirements(
                LEGAL
            )
        )

        party_names = {
            row["party_name"]
            for row in party_rows
        }

        self.stdout.write(
            "=== SGSI 4.2 ==="
        )
        self.stdout.write(
            (
                "Modo: "
                + (
                    "APPLY"
                    if options["apply"]
                    else "PREVIEW"
                )
            )
        )
        self.stdout.write(
            (
                "Partes interesadas: "
                f"{len(party_names)}"
            )
        )
        self.stdout.write(
            (
                "Filas necesidades/"
                "expectativas: "
                f"{len(party_rows)}"
            )
        )
        self.stdout.write(
            (
                "Requisitos legales: "
                f"{len(legal_rows)}"
            )
        )

        if not options[
            "apply"
        ]:
            self.stdout.write(
                (
                    "PREVIEW: no se "
                    "modificó PostgreSQL."
                )
            )
            return

        documents = {
            doc.slug: doc
            for doc in ensure_documents()
        }

        register_initial_file(
            document=documents[
                "partes-interesadas"
            ],
            file_path=PARTIES,
            version_label="V0.4",
        )

        register_initial_file(
            document=documents[
                "requisitos-legales"
            ],
            file_path=LEGAL,
            version_label="V0.15",
        )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Fuentes 4.2 cargadas. "
                    "La pantalla ya puede "
                    "mostrar los datos."
                )
            )
        )
