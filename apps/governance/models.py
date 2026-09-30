"""Gobierno del SGSI: revisión por la Dirección (9.3) y aceptación del riesgo residual (6.1.3 f)."""

from django.conf import settings
from django.db import models


class ManagementReview(models.Model):
    """Revisión por la Dirección. Las entradas de 9.3.2 se arman solas con los datos del sistema
    (se guardan como estaban el día de la revisión) y la Dirección registra sus decisiones (9.3.3)."""

    STATUS = (("draft", "En preparación"), ("approved", "Aprobada"))

    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    review_date = models.DateField()
    period_from = models.DateField(null=True, blank=True)
    period_to = models.DateField(null=True, blank=True)
    attendees = models.TextField(blank=True, help_text="Participantes, uno por línea.")
    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    inputs = models.JSONField(default=dict, blank=True, help_text="Datos del sistema al preparar la revisión (9.3.2).")
    inputs_at = models.DateTimeField(null=True, blank=True)
    # 9.3.2 b, c, e, g: lo que aporta la Dirección
    internal_external_changes = models.TextField(blank=True)
    stakeholder_changes = models.TextField(blank=True)
    stakeholder_feedback = models.TextField(blank=True)
    improvement_opportunities = models.TextField(blank=True)
    conclusions = models.TextField(blank=True)
    prepared_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-review_date",)
        verbose_name = "Revisión por la Dirección"
        verbose_name_plural = "Revisiones por la Dirección"

    def __str__(self):
        return f"{self.code} {self.title}"

    @property
    def is_locked(self):
        return self.status == "approved"


class ReviewDecision(models.Model):
    """Salida de la revisión (9.3.3): decisión con responsable y plazo, que se sigue hasta cumplirse."""

    KIND = (("mejora", "Oportunidad de mejora"), ("cambio", "Cambio en el SGSI"), ("recursos", "Necesidad de recursos"))
    STATUS = (("pendiente", "Pendiente"), ("en_curso", "En curso"), ("cumplida", "Cumplida"))

    review = models.ForeignKey(ManagementReview, on_delete=models.CASCADE, related_name="decisions")
    kind = models.CharField(max_length=10, choices=KIND, default="mejora")
    description = models.TextField()
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="review_decisions")
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pendiente")
    closed_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("status", "due_date", "pk")
        verbose_name = "Decisión de la revisión"
        verbose_name_plural = "Decisiones de la revisión"


class RiskAcceptance(models.Model):
    """Aceptación del riesgo residual por su propietario (ISO/IEC 27001 6.1.3 f; ISO/IEC 27005 8.6).
    Cada aceptación guarda el nivel que se aceptó: si el riesgo cambia, la aceptación anterior deja de valer."""

    DECISION = (("accepted", "Aceptado"), ("rejected", "No aceptado: requiere más tratamiento"))

    risk = models.ForeignKey("risks.Risk", on_delete=models.PROTECT, related_name="acceptances")
    inherent_level = models.CharField(max_length=20, blank=True)
    residual_probability = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_impact = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_level = models.CharField(max_length=20, blank=True)
    decision = models.CharField(max_length=10, choices=DECISION, default="accepted")
    justification = models.TextField()
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="risk_acceptances")
    decided_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("-decided_at",)
        verbose_name = "Aceptación de riesgo residual"
        verbose_name_plural = "Aceptaciones de riesgo residual"
