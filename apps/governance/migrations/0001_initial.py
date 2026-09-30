import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("risks", "__first__"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManagementReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
                ("title", models.CharField(max_length=200)),
                ("review_date", models.DateField()),
                ("period_from", models.DateField(blank=True, null=True)),
                ("period_to", models.DateField(blank=True, null=True)),
                ("attendees", models.TextField(blank=True, help_text="Participantes, uno por línea.")),
                ("status", models.CharField(choices=[("draft", "En preparación"), ("approved", "Aprobada")], default="draft", max_length=10)),
                ("inputs", models.JSONField(blank=True, default=dict, help_text="Datos del sistema al preparar la revisión (9.3.2).")),
                ("inputs_at", models.DateTimeField(blank=True, null=True)),
                ("internal_external_changes", models.TextField(blank=True)),
                ("stakeholder_changes", models.TextField(blank=True)),
                ("stakeholder_feedback", models.TextField(blank=True)),
                ("improvement_opportunities", models.TextField(blank=True)),
                ("conclusions", models.TextField(blank=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("prepared_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Revisión por la Dirección", "verbose_name_plural": "Revisiones por la Dirección", "ordering": ("-review_date",)},
        ),
        migrations.CreateModel(
            name="ReviewDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("mejora", "Oportunidad de mejora"), ("cambio", "Cambio en el SGSI"), ("recursos", "Necesidad de recursos")], default="mejora", max_length=10)),
                ("description", models.TextField()),
                ("due_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pendiente", "Pendiente"), ("en_curso", "En curso"), ("cumplida", "Cumplida")], default="pendiente", max_length=10)),
                ("closed_at", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("responsible", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="review_decisions", to=settings.AUTH_USER_MODEL)),
                ("review", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="decisions", to="governance.managementreview")),
            ],
            options={"verbose_name": "Decisión de la revisión", "verbose_name_plural": "Decisiones de la revisión", "ordering": ("status", "due_date", "pk")},
        ),
        migrations.CreateModel(
            name="RiskAcceptance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("inherent_level", models.CharField(blank=True, max_length=20)),
                ("residual_probability", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("residual_impact", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("residual_level", models.CharField(blank=True, max_length=20)),
                ("decision", models.CharField(choices=[("accepted", "Aceptado"), ("rejected", "No aceptado: requiere más tratamiento")], default="accepted", max_length=10)),
                ("justification", models.TextField()),
                ("decided_at", models.DateTimeField(auto_now_add=True)),
                ("is_current", models.BooleanField(db_index=True, default=True)),
                ("decided_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="risk_acceptances", to=settings.AUTH_USER_MODEL)),
                ("risk", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="acceptances", to="risks.risk")),
            ],
            options={"verbose_name": "Aceptación de riesgo residual", "verbose_name_plural": "Aceptaciones de riesgo residual", "ordering": ("-decided_at",)},
        ),
    ]
