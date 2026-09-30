import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed(apps, schema_editor):
    """Punto de partida: el Manual v0.7 (borrador) que trabaja el Oficial de Seguridad de la Información."""
    ManualReference = apps.get_model("documents", "ManualReference")
    if not ManualReference.objects.exists():
        import datetime
        ManualReference.objects.create(
            version="0.7", status="Borrador", issue_date=datetime.date(2026, 9, 14),
            prepared_by="Ana Karim Salazar", approved_by="Milton Guevara", is_current=True,
            change_note="Versión inicial registrada en el sistema (borrador en revisión; la vigente del repositorio es la V0.6).",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0008_manualdocumentrequirement"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ManualReference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(default="Manual del Sistema de Gestión de Seguridad de la Información", max_length=200)),
                ("version", models.CharField(max_length=20)),
                ("status", models.CharField(choices=[("Borrador", "Borrador"), ("Vigente", "Vigente"), ("En revisión", "En revisión")], default="Borrador", max_length=20)),
                ("issue_date", models.DateField(blank=True, null=True)),
                ("prepared_by", models.CharField(blank=True, max_length=120)),
                ("approved_by", models.CharField(blank=True, max_length=120)),
                ("change_note", models.TextField(blank=True)),
                ("is_current", models.BooleanField(db_index=True, default=True)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Versión del Manual del SGSI", "verbose_name_plural": "Versiones del Manual del SGSI", "ordering": ("-changed_at",),
                     "constraints": [models.UniqueConstraint(condition=models.Q(("is_current", True)), fields=("is_current",), name="uniq_current_manual_reference")]},
        ),
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
