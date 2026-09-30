import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField("asset", "asset_class", models.CharField(
            choices=[("equipment", "Equipo"), ("information", "Activo de información (primario)"),
                     ("support", "Activo de soporte"), ("technology", "Activo tecnológico"),
                     ("byod", "Dispositivo personal (BYOD)"), ("disposed", "Soporte dado de baja")],
            db_index=True, default="equipment", max_length=20)),
        migrations.AddField("asset", "area", models.CharField(blank=True, max_length=160)),
        migrations.AddField("asset", "process", models.CharField(blank=True, max_length=160)),
        migrations.AddField("asset", "hostname", models.CharField(blank=True, db_index=True, max_length=120)),
        migrations.AddField("asset", "owner_role", models.CharField(blank=True, max_length=160, help_text="Propietario según la matriz de riesgos (cargo).")),
        migrations.AddField("asset", "custodian_name", models.CharField(blank=True, max_length=160, help_text="Responsable cuando aún no tiene usuario en el sistema.")),
        migrations.AddField("asset", "confidentiality", models.CharField(blank=True, max_length=40)),
        migrations.AddField("asset", "integrity", models.CharField(blank=True, max_length=40)),
        migrations.AddField("asset", "availability", models.CharField(blank=True, max_length=40)),
        migrations.AddField("asset", "valuation", models.CharField(blank=True, max_length=20)),
        migrations.AddField("asset", "source", models.CharField(blank=True, max_length=255, help_text="Archivo de origen del dato.")),
        migrations.AddField("asset", "extra", models.JSONField(blank=True, default=dict)),
        migrations.AlterField("assetmovement", "movement_type", models.CharField(
            choices=[("assignment", "Asignación"), ("delivery", "Entrega"), ("return", "Devolución"),
                     ("transfer", "Transferencia"), ("replacement", "Reemplazo"), ("maintenance", "Mantenimiento"),
                     ("retirement", "Baja"), ("checkout", "Salida de la oficina"), ("checkin", "Retorno a la oficina")],
            db_index=True, max_length=20)),
        migrations.AddField("assetmovement", "person_name", models.CharField(blank=True, max_length=160)),
        migrations.AddField("assetmovement", "source", models.CharField(blank=True, max_length=255)),
        migrations.AddField("assetmovement", "import_key", models.CharField(blank=True, db_index=True, max_length=120)),
        migrations.AddField("maintenance", "person_name", models.CharField(blank=True, max_length=160, help_text="Persona revisada o a cargo del equipo.")),
        migrations.AddField("maintenance", "source", models.CharField(blank=True, max_length=255)),
        migrations.AddField("maintenance", "import_key", models.CharField(blank=True, db_index=True, max_length=120)),
        migrations.AlterModelOptions("maintenance", {"ordering": ("-performed_at",)}),
        migrations.CreateModel(
            name="AssetSoftwareSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("taken_at", models.DateField()),
                ("items", models.JSONField(default=list)),
                ("total", models.PositiveIntegerField(default=0)),
                ("weaknesses", models.PositiveIntegerField(default=0)),
                ("exploitable", models.PositiveIntegerField(default=0)),
                ("source", models.CharField(blank=True, max_length=255)),
                ("import_key", models.CharField(blank=True, db_index=True, max_length=120)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="software_snapshots", to="assets.asset")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assets_assetsoftwaresnapshot_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assets_assetsoftwaresnapshot_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-taken_at",)},
        ),
    ]
