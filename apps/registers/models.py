"""Registros del SGSI que la empresa llevaba en Excel (plan de capacitación, software autorizado,
obligaciones del OSE...). Cada registro define sus campos en schemas.py; aquí solo se guardan las filas."""

from django.conf import settings
from django.db import models


class RegisterEntry(models.Model):
    register = models.CharField(max_length=60, db_index=True, verbose_name="Registro")
    year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True, verbose_name="Año")
    section = models.CharField(max_length=40, blank=True, verbose_name="Sección")
    order = models.PositiveIntegerField(default=0, verbose_name="Orden")
    data = models.JSONField(default=dict, verbose_name="Datos")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ("register", "year", "section", "order", "id")
        verbose_name = "Fila de registro"
        verbose_name_plural = "Filas de registros"
        permissions = [("import_registerentry", "Puede importar y reemplazar registros desde Excel")]

    def __str__(self):
        return f"{self.register} {self.year or ''} #{self.pk}"


class RegisterImport(models.Model):
    register = models.CharField(max_length=60)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    file_name = models.CharField(max_length=255)
    rows = models.PositiveIntegerField(default=0)
    replaced = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Importación de registro"
        verbose_name_plural = "Importaciones de registros"
