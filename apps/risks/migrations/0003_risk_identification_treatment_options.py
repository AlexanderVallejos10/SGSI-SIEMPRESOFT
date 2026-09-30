# Escrita a mano. Verificar con: python manage.py makemigrations risks --check --dry-run

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0001_initial'),
        ('controls', '0003_controldocumentassignment'),
        ('risks', '0002_risk_category_risk_event_risk_existing_controls_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='risk',
            name='identification_type',
            field=models.CharField(choices=[('events', 'Basado en eventos'), ('assets', 'Basado en activos'), ('project', 'Riesgo de proyecto')], db_index=True, default='events', max_length=10, verbose_name='Tipo de identificación'),
        ),
        migrations.AddField(
            model_name='risk',
            name='project_name',
            field=models.CharField(blank=True, max_length=200, verbose_name='Proyecto'),
        ),
        migrations.AddField(
            model_name='risk',
            name='affected_asset_text',
            field=models.TextField(blank=True, verbose_name='Activo o proceso afectado (según la fuente)'),
        ),
        migrations.AddField(
            model_name='risk',
            name='affected_assets',
            field=models.ManyToManyField(blank=True, related_name='affected_by_risks', to='assets.asset', verbose_name='Activos afectados'),
        ),
        migrations.AddField(
            model_name='risk',
            name='operational_scenario',
            field=models.TextField(blank=True, verbose_name='Escenario operacional'),
        ),
        migrations.AddField(
            model_name='risk',
            name='finding_origin',
            field=models.CharField(blank=True, max_length=60, verbose_name='Origen del hallazgo'),
        ),
        migrations.AddField(
            model_name='risk',
            name='evidence_reference',
            field=models.TextField(blank=True, verbose_name='Referencia / evidencia'),
        ),
        migrations.AddField(
            model_name='risktreatment',
            name='control',
            field=models.ForeignKey(blank=True, limit_choices_to={'framework__code': 'ISO27001-2022'}, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='risk_treatments', to='controls.control', verbose_name='Control del Anexo A (ISO/IEC 27001:2022)'),
        ),
        migrations.AddField(
            model_name='risktreatment',
            name='third_party',
            field=models.CharField(blank=True, max_length=200, verbose_name='Tercero que asume el riesgo'),
        ),
        migrations.AddField(
            model_name='risktreatment',
            name='third_party_responsibilities',
            field=models.TextField(blank=True, verbose_name='Responsabilidades del tercero'),
        ),
        migrations.AddField(
            model_name='risktreatment',
            name='contract_reference',
            field=models.CharField(blank=True, max_length=200, verbose_name='Contrato o acuerdo'),
        ),
        migrations.AddField(
            model_name='risktreatment',
            name='avoidance_method',
            field=models.TextField(blank=True, verbose_name='Cómo se evita el riesgo'),
        ),
        migrations.AddField(
            model_name='risktreatment',
            name='acceptance_justification',
            field=models.TextField(blank=True, verbose_name='Justificación de la aceptación'),
        ),
        migrations.AlterField(
            model_name='risktreatment',
            name='option',
            field=models.CharField(choices=[('1. Elección de controles', '1. Elección de controles'), ('2. Transferencia de riesgos a terceros', '2. Transferencia de riesgos a terceros'), ('3. Evitar el riesgo', '3. Evitar el riesgo'), ('4. Aceptación del riesgo', '4. Aceptación del riesgo')], max_length=60, verbose_name='Opción de tratamiento'),
        ),
        migrations.AlterField(
            model_name='risktreatment',
            name='action',
            field=models.TextField(verbose_name='Actividad a implementar'),
        ),
    ]
