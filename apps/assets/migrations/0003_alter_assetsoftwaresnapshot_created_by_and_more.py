import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Solo ajusta cómo se registra el nombre de la relación (plantilla del modelo base). No cambia tablas."""

    dependencies = [
        ("assets", "0002_trazabilidad_activos"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="assetsoftwaresnapshot",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="%(app_label)s_%(class)s_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="assetsoftwaresnapshot",
            name="updated_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="%(app_label)s_%(class)s_updated", to=settings.AUTH_USER_MODEL),
        ),
    ]
