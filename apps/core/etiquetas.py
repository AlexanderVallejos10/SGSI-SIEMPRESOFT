from django.utils.text import capfirst

CAMPOS = {
    "access": "Acceso", "access_level": "Nivel de acceso", "action": "Acción", "active": "Activo",
    "affected_user": "Usuario afectado", "applicability": "Aplicabilidad", "approval_reference": "Referencia de aprobación",
    "approved_at": "Aprobado el", "approved_by": "Aprobado por", "approver": "Aprobador", "area": "Área",
    "assessed_at": "Evaluado el", "asset": "Activo", "asset_class": "Clase de activo", "asset_type": "Tipo de activo",
    "assets": "Activos", "audit": "Auditoría", "audit_type": "Tipo de auditoría",
    "authorization_authority": "Autoridad que autoriza", "authorization_date": "Fecha de autorización",
    "availability": "Disponibilidad", "brand": "Marca", "business_code": "Código de colaborador",
    "calculation_formula": "Fórmula de cálculo", "calculation_period": "Periodo de cálculo", "category": "Categoría",
    "checksum_sha256": "Huella SHA-256", "classification": "Clasificación", "clause": "Cláusula",
    "closed_date": "Fecha de cierre", "code": "Código", "color": "Color", "comments": "Comentarios",
    "compliance_formula": "Fórmula de cumplimiento", "compliance_percent": "Cumplimiento (%)",
    "compliance_raw": "Cumplimiento (valor original)", "confidentiality": "Confidencialidad", "consequence": "Consecuencia",
    "control": "Control", "controls": "Controles", "created_at": "Creado el", "created_by": "Creado por",
    "credentials_issued_at": "Credenciales emitidas el", "criteria": "Criterios", "criterion": "Criterio",
    "criticality": "Criticidad", "current_number_format": "Formato numérico", "current_value_numeric": "Valor actual",
    "current_value_raw": "Valor actual (original)", "custodian": "Custodio", "custodian_name": "Nombre del custodio",
    "cve": "CVE", "cvss": "CVSS", "decision": "Decisión", "description": "Descripción", "destination": "Destino",
    "detail": "Detalle", "detected_at": "Detectada el", "document": "Documento", "document_number": "N.° de documento",
    "document_type": "Tipo de documento", "document_version": "Versión del documento", "documents": "Documentos",
    "domain": "Dominio", "due_date": "Fecha límite", "edr_antivirus": "EDR / antivirus",
    "effectiveness_notes": "Notas de eficacia", "effectiveness_verified_at": "Eficacia verificada el",
    "effectiveness_verified_by": "Eficacia verificada por", "employment_end": "Fin de vínculo laboral",
    "employment_start": "Inicio de vínculo laboral", "encrypted": "Cifrado", "end_date": "Fecha de fin",
    "event": "Evento", "evidence": "Evidencia", "evidence_date": "Fecha de la evidencia",
    "evidence_reference": "Referencia de la evidencia", "existing_controls": "Controles existentes",
    "external_reference": "Referencia externa", "extra": "Datos adicionales", "factor": "Factor",
    "factor_type": "Tipo de factor", "file": "Archivo", "finding": "Hallazgo", "finding_type": "Tipo de hallazgo",
    "framework": "Marco de referencia", "hostname": "Nombre del equipo", "id": "Identificador",
    "identified_at": "Identificado el", "impact": "Impacto", "implementation_status": "Estado de implementación",
    "import_key": "Clave de importación", "incident": "Incidente", "incident_type": "Tipo de incidente",
    "indicator": "Indicador", "inherent_score": "Nivel de riesgo inherente", "integrity": "Integridad",
    "involved_areas": "Áreas involucradas", "involved_positions": "Puestos involucrados", "is_active": "Activo",
    "is_clause_heading": "Es título de cláusula", "is_current": "Vigente", "is_in_scope": "Dentro del alcance",
    "is_privileged": "Acceso privilegiado", "justification": "Justificación", "kind": "Tipo", "label": "Etiqueta",
    "last_review_at": "Última revisión", "last_seen_at": "Última actividad", "lead_auditor": "Auditor líder",
    "level": "Nivel", "location": "Ubicación", "maintenance_type": "Tipo de mantenimiento",
    "management_system": "Sistema de gestión", "manager": "Jefe inmediato", "matrix_type": "Tipo de matriz",
    "maturity_level": "Nivel de madurez", "mdm": "Gestión de dispositivos (MDM)", "measurement_id": "N.° de medición",
    "measurement_objective": "Objetivo de la medición", "method_resources": "Método y recursos",
    "mfa_enabled": "Doble factor activado", "model": "Modelo", "motivation": "Motivo",
    "movement_type": "Tipo de movimiento", "must_change_password": "Debe cambiar la contraseña", "name": "Nombre",
    "next_due_at": "Próxima fecha", "next_review_at": "Próxima revisión", "notes": "Notas", "objective": "Objetivo",
    "objective_code": "Código del objetivo", "occurred_at": "Fecha y hora", "operating_system": "Sistema operativo",
    "origin": "Origen", "original_name": "Nombre original", "owner": "Propietario",
    "owner_position": "Puesto propietario", "owner_role": "Cargo propietario", "parent": "Depende de",
    "participants": "Participantes", "password_changed_at": "Contraseña cambiada el",
    "password_changes": "Cambios de contraseña", "patch_status": "Estado de parches", "pdca_cycle": "Ciclo PHVA",
    "performed_at": "Realizado el", "period": "Periodo", "person_name": "Persona", "photo": "Foto",
    "position": "Puesto", "probability": "Probabilidad", "process": "Proceso",
    "reason": "Motivo", "recommended_actions": "Acciones recomendadas", "relation_type": "Tipo de relación",
    "replaced_asset": "Activo reemplazado", "report": "Informe", "reporter": "Reportado por",
    "residual_impact": "Impacto residual", "residual_probability": "Probabilidad residual",
    "residual_score": "Nivel de riesgo residual", "resources": "Recursos", "responsible": "Responsable",
    "result": "Resultado", "retention_policy": "Política de retención", "review_frequency": "Frecuencia de revisión",
    "reviewed_at": "Revisado el", "reviewer": "Revisor", "revoked_at": "Revocado el", "risk": "Riesgo",
    "risks": "Riesgos", "role_profile": "Perfil del rol", "root_cause": "Causa raíz", "scenario": "Escenario",
    "scope": "Alcance", "serial": "N.° de serie", "severity": "Severidad", "sgsi_process": "Proceso del SGSI",
    "sgsi_sections": "Secciones del SGSI", "slug": "Identificador corto", "snapshot": "Versión del tablero",
    "solution": "Solución", "sort_order": "Orden", "source": "Origen", "source_artifact": "Archivo de origen",
    "source_code": "Código en la fuente", "source_compliance_override": "Cumplimiento según la fuente",
    "source_description": "Descripción en la fuente", "source_document": "Documento de origen",
    "source_end": "Fin en la fuente", "source_group": "Grupo en la fuente", "source_identity_key": "Clave en la fuente",
    "source_label": "Etiqueta en la fuente", "source_reference": "Referencia en la fuente",
    "source_row": "Fila en la fuente", "source_sheet": "Hoja en la fuente", "source_start": "Inicio en la fuente",
    "source_verified": "Verificado con la fuente", "start_date": "Fecha de inicio", "status": "Estado",
    "status_as_of": "Estado confirmado al", "supporting_reference": "Sustento", "system": "Sistema",
    "target": "Destino", "technical_implementer": "Implementador técnico", "technician": "Técnico",
    "threat": "Amenaza", "title": "Título", "update_period": "Periodo de actualización", "updated_at": "Actualizado el",
    "updated_by": "Actualizado por", "user": "Usuario", "validated_at": "Validado el", "validated_by": "Validado por",
    "valuation": "Valoración", "version_label": "Versión", "vulnerability": "Vulnerabilidad", "x": "Posición X",
    "y": "Posición Y", "username": "Usuario", "first_name": "Nombres", "last_name": "Apellidos",
    "email": "Correo", "is_staff": "Acceso al panel técnico", "is_superuser": "Superusuario",
    "last_login": "Último ingreso", "date_joined": "Fecha de alta", "groups": "Roles",
    "user_permissions": "Permisos directos", "password": "Contraseña",
    "is_primary": "Puesto principal", "max_occupants": "Máximo de ocupantes", "is_critical": "Puesto crítico",
    "method": "Método", "responsible_text": "Responsable", "responsible_position": "Puesto responsable",
    "current_value": "Valor actual", "action_plan": "Plan de acción", "record_label": "Registro",
    "weight": "Peso",
}

MODELOS = {
    "asset": ("Activo", "Activos"), "assetmovement": ("Movimiento de activo", "Movimientos de activos"),
    "maintenance": ("Mantenimiento", "Mantenimientos"), "audit": ("Auditoría", "Auditorías"),
    "finding": ("Hallazgo", "Hallazgos"), "improvementaction": ("Acción de mejora", "Acciones de mejora"),
    "control": ("Control", "Controles"), "controlevidence": ("Evidencia de control", "Evidencias de controles"),
    "document": ("Documento", "Documentos"), "evidence": ("Evidencia", "Evidencias"),
    "incident": ("Incidente", "Incidentes"), "incidentevent": ("Evento de incidente", "Eventos de incidentes"),
    "vulnerability": ("Vulnerabilidad", "Vulnerabilidades"), "risk": ("Riesgo", "Riesgos"),
    "riskassessment": ("Evaluación de riesgo", "Evaluaciones de riesgo"),
    "risktreatment": ("Tratamiento de riesgo", "Tratamientos de riesgo"),
    "objectivealignment": ("Alineamiento de objetivos", "Alineamientos de objetivos"),
    "securityobjective": ("Objetivo de seguridad", "Objetivos de seguridad"),
    "strategicfactor": ("Factor estratégico", "Factores estratégicos"),
    "processcategory": ("Categoría de procesos", "Categorías de procesos"),
    "processcategoryrelation": ("Relación entre categorías", "Relaciones entre categorías"),
    "processnode": ("Proceso", "Procesos"), "processrelation": ("Relación entre procesos", "Relaciones entre procesos"),
    "processreferencedocument": ("Documento de referencia", "Documentos de referencia"),
    "processreferenceversion": ("Versión de referencia", "Versiones de referencia"),
    "legalrequirement": ("Requisito legal", "Requisitos legales"),
}


def _automatico(field):
    return str(getattr(field, "verbose_name", "")) == field.name.replace("_", " ")


def etiqueta_campo(field):
    if _automatico(field):
        return CAMPOS.get(field.name, capfirst(field.name.replace("_", " ")))
    return capfirst(str(field.verbose_name))


def etiqueta_modelo(model, plural=False):
    nombres = MODELOS.get(model._meta.model_name)
    if nombres:
        return nombres[1] if plural else nombres[0]
    return capfirst(str(model._meta.verbose_name_plural if plural else model._meta.verbose_name))


def traducir_formulario(form):
    model = getattr(getattr(form, "_meta", None), "model", None)
    if model is None:
        return form
    for name, campo in form.fields.items():
        try:
            field = model._meta.get_field(name)
        except Exception:
            continue
        if _automatico(field) and campo.label in (None, capfirst(field.verbose_name)):
            campo.label = etiqueta_campo(field)
    return form
