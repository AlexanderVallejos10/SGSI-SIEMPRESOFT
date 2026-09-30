# Escrita a mano. Verificar con: python manage.py makemigrations processes --check --dry-run
#
# 1. Agrega las partes interesadas de entrada y salida (Cliente / PSE, Cliente / PSE / SUNAT).
# 2. Pasa la coordenada y de absoluta a relativa a la franja, para que las franjas crezcan
#    solas y un proceso pueda cambiar de categoría sin descuadrar el mapa.

from django.db import migrations, models

OLD_LANE_TOP = {"strategic": 45, "operational": 150, "support": 500}
PARTIES = (
    ("PROC-ENTRADA", "Partes interesadas (entrada)", "input", 5),
    ("PROC-SALIDA", "Partes interesadas (salida)", "output", 95),
)


def forwards(apps, schema_editor):
    ProcessCategory = apps.get_model("processes", "ProcessCategory")
    ProcessNode = apps.get_model("processes", "ProcessNode")
    for code, name, kind, order in PARTIES:
        if not ProcessCategory.objects.filter(kind=kind).exists():
            ProcessCategory.objects.create(code=code, name=name, kind=kind, sort_order=order)
    for node in ProcessNode.objects.select_related("category"):
        top = OLD_LANE_TOP.get(node.category.kind)
        if top is not None:
            node.y = max(0, node.y - top)
            node.save(update_fields=["y"])


def backwards(apps, schema_editor):
    ProcessNode = apps.get_model("processes", "ProcessNode")
    for node in ProcessNode.objects.select_related("category"):
        top = OLD_LANE_TOP.get(node.category.kind)
        if top is not None:
            node.y = min(650, node.y + top)
            node.save(update_fields=["y"])


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0003_processnode_primary_area'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processcategory',
            name='kind',
            field=models.CharField(choices=[('strategic', 'Proceso estratégico'), ('operational', 'Proceso operativo'), ('support', 'Proceso de apoyo'), ('input', 'Parte interesada (entrada)'), ('output', 'Parte interesada (salida)')], db_index=True, max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='processnode',
            name='y',
            field=models.PositiveSmallIntegerField(default=40),
        ),
        migrations.RunPython(forwards, backwards),
    ]
