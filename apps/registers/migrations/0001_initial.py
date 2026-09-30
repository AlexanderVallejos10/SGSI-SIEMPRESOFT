import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RegisterEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("register", models.CharField(db_index=True, max_length=60, verbose_name="Registro")),
                ("year", models.PositiveSmallIntegerField(blank=True, db_index=True, null=True, verbose_name="Año")),
                ("section", models.CharField(blank=True, max_length=40, verbose_name="Sección")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Orden")),
                ("data", models.JSONField(default=dict, verbose_name="Datos")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Fila de registro",
                "verbose_name_plural": "Filas de registros",
                "ordering": ("register", "year", "section", "order", "id"),
                "permissions": [("import_registerentry", "Puede importar y reemplazar registros desde Excel")],
            },
        ),
        migrations.CreateModel(
            name="RegisterImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("register", models.CharField(max_length=60)),
                ("year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("file_name", models.CharField(max_length=255)),
                ("rows", models.PositiveIntegerField(default=0)),
                ("replaced", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Importación de registro",
                "verbose_name_plural": "Importaciones de registros",
                "ordering": ("-created_at",),
            },
        ),
    ]
