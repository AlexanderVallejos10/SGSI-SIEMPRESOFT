# Crea Cliente / PSE (entrada) y Cliente / PSE / SUNAT (salida) con los flujos del mapa V0.15,
# sin depender del comando configure_sgsi_structure. Solo actúa si todavía no existen.

from django.db import migrations

PARTIES = (
    ("PARTE-CLIENTE-PSE", "Cliente / PSE", "input", "PROC-ENTRADA", "Partes interesadas (entrada)", 5),
    ("PARTE-CLIENTE-SUNAT", "Cliente / PSE / SUNAT", "output", "PROC-SALIDA", "Partes interesadas (salida)", 95),
)
FLOWS = (
    ("PARTE-CLIENTE-PSE", "PROC-OSE"),
    ("PARTE-CLIENTE-PSE", "PROC-VENTAS"),
    ("PROC-OSE", "PARTE-CLIENTE-SUNAT"),
    ("PROC-SOPORTE", "PARTE-CLIENTE-SUNAT"),
    ("PROC-PROD", "PARTE-CLIENTE-SUNAT"),
)


def forwards(apps, schema_editor):
    ProcessCategory = apps.get_model("processes", "ProcessCategory")
    ProcessNode = apps.get_model("processes", "ProcessNode")
    ProcessRelation = apps.get_model("processes", "ProcessRelation")
    created = set()
    for code, name, kind, cat_code, cat_name, order in PARTIES:
        category = ProcessCategory.objects.filter(kind=kind).first()
        if category is None:
            category = ProcessCategory.objects.create(code=cat_code, name=cat_name, kind=kind, sort_order=order)
        if not ProcessNode.objects.filter(code=code).exists():
            ProcessNode.objects.create(
                code=code, name=name, category=category, x=0, y=0, is_in_scope=False, is_external=True
            )
            created.add(code)
    for source, target in FLOWS:
        if source not in created and target not in created:
            continue
        a = ProcessNode.objects.filter(code=source).first()
        b = ProcessNode.objects.filter(code=target).first()
        if a and b and not ProcessRelation.objects.filter(source=a, target=b, relation_type="flow").exists():
            ProcessRelation.objects.create(source=a, target=b, relation_type="flow")


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0004_lane_relative_layout_parties'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
