from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.assets.models import Asset
from apps.controls.models import Control
from apps.core.models import TraceableModel
from apps.documents.models import Evidence

ANNEX_A_FRAMEWORK = "ISO27001-2022"


class RiskStatus(models.TextChoices):
    IDENTIFIED = "identified", "Identificado"
    TREATMENT = "treatment", "En tratamiento"
    ACCEPTED = "accepted", "Aceptado"
    CLOSED = "closed", "Cerrado"


class IdentificationType(models.TextChoices):
    """Tres identificaciones que pidió la auditoría, cada una con su tratamiento."""

    EVENTS = "events", "Basado en eventos"
    ASSETS = "assets", "Basado en activos"
    PROJECT = "project", "Riesgo de proyecto"


class Risk(TraceableModel):
    origin = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=100, blank=True)
    event = models.TextField(blank=True)
    motivation = models.TextField(blank=True)
    existing_controls = models.TextField(blank=True)
    owner_position = models.ForeignKey(
        "organization.Position", null=True, blank=True, on_delete=models.PROTECT, related_name="owned_risks"
    )
    is_active = models.BooleanField(default=True)

    identification_type = models.CharField(
        max_length=10,
        choices=IdentificationType.choices,
        default=IdentificationType.EVENTS,
        db_index=True,
        verbose_name="Tipo de identificación",
    )
    project_name = models.CharField(max_length=200, blank=True, verbose_name="Proyecto")
    affected_asset_text = models.TextField(blank=True, verbose_name="Activo o proceso afectado (según la fuente)")
    affected_assets = models.ManyToManyField(
        Asset, blank=True, related_name="affected_by_risks", verbose_name="Activos afectados"
    )
    operational_scenario = models.TextField(blank=True, verbose_name="Escenario operacional")
    finding_origin = models.CharField(max_length=60, blank=True, verbose_name="Origen del hallazgo")
    evidence_reference = models.TextField(blank=True, verbose_name="Referencia / evidencia")

    code = models.CharField(max_length=50, unique=True, db_index=True)
    process = models.CharField(max_length=160, db_index=True)
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT, related_name="risks")
    scenario = models.TextField()
    threat = models.CharField(max_length=255, blank=True)
    vulnerability = models.CharField(max_length=255, blank=True)
    consequence = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="owned_risks"
    )
    controls = models.ManyToManyField(Control, blank=True, related_name="risks")
    status = models.CharField(
        max_length=20, choices=RiskStatus.choices, default=RiskStatus.IDENTIFIED, db_index=True
    )
    identified_at = models.DateField(null=True, blank=True)

    def clean(self):
        super().clean()
        errors = {}
        if self.identification_type == IdentificationType.PROJECT and not self.project_name.strip():
            errors["project_name"] = "Indique el proyecto al que pertenece este riesgo."
        if (
            self.identification_type == IdentificationType.ASSETS
            and not self.asset_id
            and not self.affected_asset_text.strip()
        ):
            errors["affected_asset_text"] = "Un riesgo basado en activos debe indicar el activo afectado."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.code} - {self.process}"


class RiskAssessment(TraceableModel):
    risk = models.ForeignKey(Risk, on_delete=models.PROTECT, related_name="assessments")
    assessed_at = models.DateTimeField()
    probability = models.PositiveSmallIntegerField()
    impact = models.PositiveSmallIntegerField()
    inherent_score = models.DecimalField(max_digits=8, decimal_places=2)
    residual_probability = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_impact = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-assessed_at",)


class TreatmentOption(models.TextChoices):
    # Los valores son los mismos textos de la matriz, así los datos ya importados siguen siendo válidos.
    CONTROLS = "1. Elección de controles", "1. Elección de controles"
    TRANSFER = "2. Transferencia de riesgos a terceros", "2. Transferencia de riesgos a terceros"
    AVOID = "3. Evitar el riesgo", "3. Evitar el riesgo"
    ACCEPT = "4. Aceptación del riesgo", "4. Aceptación del riesgo"


class RiskTreatment(TraceableModel):
    start_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    source_start = models.CharField(max_length=100, blank=True)
    source_end = models.CharField(max_length=100, blank=True)
    residual_probability = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_impact = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    risk = models.ForeignKey(Risk, on_delete=models.PROTECT, related_name="treatments")
    option = models.CharField(
        max_length=60, choices=TreatmentOption.choices, verbose_name="Opción de tratamiento"
    )
    control = models.ForeignKey(
        Control,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="risk_treatments",
        limit_choices_to={"framework__code": ANNEX_A_FRAMEWORK},
        verbose_name="Control del Anexo A (ISO/IEC 27001:2022)",
    )
    action = models.TextField(verbose_name="Actividad a implementar")
    third_party = models.CharField(max_length=200, blank=True, verbose_name="Tercero que asume el riesgo")
    third_party_responsibilities = models.TextField(blank=True, verbose_name="Responsabilidades del tercero")
    contract_reference = models.CharField(max_length=200, blank=True, verbose_name="Contrato o acuerdo")
    avoidance_method = models.TextField(blank=True, verbose_name="Cómo se evita el riesgo")
    acceptance_justification = models.TextField(blank=True, verbose_name="Justificación de la aceptación")
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="risk_treatments",
    )
    resources = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, default="pending")
    evidence = models.ForeignKey(
        Evidence, null=True, blank=True, on_delete=models.PROTECT, related_name="risk_treatments"
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_risk_treatments",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    def missing_requirements(self):
        """Lo que exige cada opción de tratamiento. Lo usan el formulario y el importador."""
        missing = {}
        if self.option == TreatmentOption.CONTROLS and not self.control_id:
            missing["control"] = "Seleccione el control del Anexo A que se implementará (va a la Declaración de Aplicabilidad)."
        elif self.option == TreatmentOption.TRANSFER:
            if not self.third_party.strip():
                missing["third_party"] = "Indique a qué tercero se transfiere el riesgo."
            if not self.third_party_responsibilities.strip():
                missing["third_party_responsibilities"] = "Detalle las responsabilidades del tercero sobre el riesgo."
            if not self.contract_reference.strip() and not self.evidence_id:
                missing["contract_reference"] = "Registre el contrato o adjunte la evidencia del acuerdo con el tercero."
        elif self.option == TreatmentOption.AVOID and not self.avoidance_method.strip():
            missing["avoidance_method"] = "Explique cómo se evitará el riesgo (descontinuar, cancelar o dejar de usar el proceso)."
        elif self.option == TreatmentOption.ACCEPT and not self.acceptance_justification.strip():
            missing["acceptance_justification"] = "Justifique la aceptación, por ejemplo, por qué el control costaría más que el riesgo."
        return missing

    def clean(self):
        super().clean()
        errors = self.missing_requirements()
        if self.control_id and self.control.framework.code != ANNEX_A_FRAMEWORK:
            errors["control"] = "El control debe pertenecer al Anexo A de ISO/IEC 27001:2022."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.risk.code} · {self.option}"
