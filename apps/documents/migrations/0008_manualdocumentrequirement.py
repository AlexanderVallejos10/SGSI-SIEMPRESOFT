import uuid

from django.db import migrations, models


def seed(apps, schema_editor):
    """Carga lo que exige el Manual del SGSI v0.7. Después se mantiene desde /admin/."""
    from apps.dashboard.manual_sgsi import MANUAL_DOCUMENTS

    Requirement = apps.get_model("documents", "ManualDocumentRequirement")
    if Requirement.objects.exists():
        return
    for numeral, docs in MANUAL_DOCUMENTS.items():
        for order, doc in enumerate(docs, start=1):
            Requirement.objects.create(
                numeral=numeral,
                name=doc["name"],
                location=doc.get("location", ""),
                manual_version="0.7",
                sort_order=order * 10,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0007_documentsectionassignment"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManualDocumentRequirement",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("numeral", models.CharField(db_index=True, max_length=20, verbose_name="Numeral")),
                ("name", models.CharField(max_length=255, verbose_name="Documento, tal como lo nombra el Manual")),
                ("location", models.TextField(blank=True, verbose_name="Ubicación según el Manual")),
                ("manual_version", models.CharField(blank=True, max_length=20, verbose_name="Versión del Manual")),
                ("sort_order", models.PositiveSmallIntegerField(default=10, verbose_name="Orden")),
                ("is_active", models.BooleanField(default=True, verbose_name="Vigente")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Documento exigido por el Manual",
                "verbose_name_plural": "Documentos exigidos por el Manual",
                "ordering": ("numeral", "sort_order", "name"),
            },
        ),
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
