from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.documents.models import (
    Document,
    DocumentVersion,
    Evidence,
    SourceArtifact,
)
from apps.documents.models_classification import (
    SourceArtifactClassification,
)


def format_default(field):
    if field.has_default():
        value = field.default
        if callable(value):
            return getattr(value, "__name__", repr(value))
        return repr(value)
    return "-"


class Command(BaseCommand):
    help = (
        "Inspecciona el esquema real de Document/DocumentVersion/Evidence "
        "y resume la clasificación persistida antes de promover fuentes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--top",
            type=int,
            default=50,
            help="Máximo de combinaciones a mostrar.",
        )

    def handle(self, *args, **options):
        top = options["top"]

        canonical = SourceArtifact.objects.filter(
            duplicate_of__isnull=True
        )
        classifications = SourceArtifactClassification.objects.all()

        self.stdout.write("=== ESTADO PERSISTIDO ===")
        self.stdout.write(
            f"SourceArtifact total: {SourceArtifact.objects.count()}"
        )
        self.stdout.write(
            f"SourceArtifact canónicos: {canonical.count()}"
        )
        self.stdout.write(
            f"Clasificaciones guardadas: {classifications.count()}"
        )
        self.stdout.write(
            "Canónicos sin clasificación: "
            f"{canonical.filter(classification__isnull=True).count()}"
        )
        self.stdout.write(
            "Duplicados con clasificación: "
            f"{SourceArtifact.objects.filter(duplicate_of__isnull=False, classification__isnull=False).count()}"
        )
        self.stdout.write("")
        self.stdout.write(
            f"Document existentes: {Document.objects.count()}"
        )
        self.stdout.write(
            f"DocumentVersion existentes: {DocumentVersion.objects.count()}"
        )
        self.stdout.write(
            f"Evidence existentes: {Evidence.objects.count()}"
        )

        for model in (Document, DocumentVersion, Evidence):
            self.stdout.write("")
            self.stdout.write(
                f"=== MODELO {model.__name__} ==="
            )

            for field in model._meta.fields:
                relation = "-"
                if getattr(field, "remote_field", None):
                    remote_model = getattr(
                        field.remote_field,
                        "model",
                        None,
                    )
                    relation = getattr(
                        remote_model,
                        "__name__",
                        str(remote_model),
                    )

                choices = "-"
                if field.choices:
                    choices = ", ".join(
                        f"{value}={label}"
                        for value, label in field.flatchoices
                    )

                self.stdout.write(
                    f"{field.name} | "
                    f"{field.__class__.__name__} | "
                    f"null={field.null} | "
                    f"blank={field.blank} | "
                    f"default={format_default(field)} | "
                    f"relation={relation} | "
                    f"choices={choices}"
                )

        self.stdout.write("")
        self.stdout.write("=== MATRIZ FAMILIA x RELEVANCIA ===")

        rows = (
            classifications
            .values("family_hint", "sgsi_relevance")
            .annotate(total=Count("id"))
            .order_by("-total", "family_hint", "sgsi_relevance")
        )

        for row in rows[:top]:
            self.stdout.write(
                f"{row['total']:>5} | "
                f"{row['family_hint']:<24} | "
                f"{row['sgsi_relevance']}"
            )

        self.stdout.write("")
        self.stdout.write("=== MATRIZ FAMILIA x CICLO DE VIDA ===")

        rows = (
            classifications
            .values("family_hint", "lifecycle_hint")
            .annotate(total=Count("id"))
            .order_by("-total", "family_hint", "lifecycle_hint")
        )

        for row in rows[:top]:
            self.stdout.write(
                f"{row['total']:>5} | "
                f"{row['family_hint']:<24} | "
                f"{row['lifecycle_hint']}"
            )

        self.stdout.write("")
        self.stdout.write("=== BANDERAS DE PROMOCIÓN ===")
        self.stdout.write(
            "Document candidate: "
            f"{classifications.filter(is_document_candidate=True).count()}"
        )
        self.stdout.write(
            "Evidence candidate: "
            f"{classifications.filter(is_evidence_candidate=True).count()}"
        )
        self.stdout.write(
            "Dashboard candidate: "
            f"{classifications.filter(is_dashboard_candidate=True).count()}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Inspección finalizada sin modificar la base de datos."
            )
        )
