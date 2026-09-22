from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction


BUSINESS_PERMISSIONS = {
    "accounts.user": [
        ("review_access", "Puede revisar accesos de usuarios"),
        ("deactivate_user", "Puede desactivar usuarios"),
    ],

    "documents.document": [
        ("approve_document", "Puede aprobar documentos"),
        ("publish_document", "Puede publicar documentos"),
        ("obsolete_document", "Puede declarar documentos obsoletos"),
        ("export_document", "Puede exportar documentos"),
    ],

    "controls.control": [
        ("assess_control", "Puede evaluar controles"),
        ("link_evidence_control", "Puede vincular evidencias a controles"),
        ("export_control", "Puede exportar controles"),
    ],

    "assets.asset": [
        ("assign_asset", "Puede asignar activos"),
        ("return_asset", "Puede registrar devolución de activos"),
        ("replace_asset", "Puede registrar reemplazo de activos"),
        ("export_asset", "Puede exportar activos"),
    ],

    "risks.risk": [
        ("approve_risk", "Puede aprobar riesgos"),
        ("close_risk", "Puede cerrar riesgos"),
        ("export_risk", "Puede exportar riesgos"),
    ],

    "incidents.incident": [
        ("close_incident", "Puede cerrar incidentes"),
        ("export_incident", "Puede exportar incidentes"),
    ],

    "incidents.vulnerability": [
        ("close_vulnerability", "Puede cerrar vulnerabilidades"),
    ],

    "assurance.audit": [
        ("close_audit", "Puede cerrar auditorías"),
        ("export_audit", "Puede exportar auditorías"),
    ],

    "assurance.finding": [
        ("close_finding", "Puede cerrar hallazgos"),
    ],

    "assurance.improvementaction": [
        ("close_improvement_action", "Puede cerrar acciones de mejora"),
    ],
}


ROLE_BUSINESS_PERMISSIONS = {
    "Administrador SGSI": {"*"},

    "Oficial de Seguridad de la Información": {
        "accounts.review_access",
        "accounts.deactivate_user",

        "documents.approve_document",
        "documents.publish_document",
        "documents.obsolete_document",
        "documents.export_document",

        "controls.assess_control",
        "controls.link_evidence_control",
        "controls.export_control",

        "risks.approve_risk",
        "risks.close_risk",
        "risks.export_risk",

        "incidents.close_incident",
        "incidents.export_incident",
        "incidents.close_vulnerability",

        "assurance.close_audit",
        "assurance.close_finding",
        "assurance.close_improvement_action",
        "assurance.export_audit",
    },

    "Alta Dirección": {
        "documents.approve_document",
        "risks.approve_risk",
        "assurance.export_audit",
    },

    "Responsable TI": {
        "assets.assign_asset",
        "assets.return_asset",
        "assets.replace_asset",
        "assets.export_asset",
        "incidents.close_incident",
        "incidents.close_vulnerability",
    },

    "Recursos Humanos": {
        "accounts.review_access",
    },

    "Responsable de Activos": {
        "assets.assign_asset",
        "assets.return_asset",
        "assets.replace_asset",
        "assets.export_asset",
    },

    "Propietario de Riesgo": {
        "risks.close_risk",
        "risks.export_risk",
    },

    "Responsable de Control": {
        "controls.assess_control",
        "controls.link_evidence_control",
        "controls.export_control",
    },

    "Auditor": {
        "assurance.close_audit",
        "assurance.close_finding",
        "assurance.export_audit",
    },

    "Responsable Documental": {
        "documents.publish_document",
        "documents.obsolete_document",
        "documents.export_document",
    },

    "Usuario / Colaborador": set(),

    "Consulta / Lector": set(),
}


def _all_permission_refs():
    refs = set()

    for object_ref, definitions in BUSINESS_PERMISSIONS.items():
        app_label, _ = object_ref.split(".", 1)

        for codename, _ in definitions:
            refs.add(f"{app_label}.{codename}")

    return refs


@transaction.atomic
def sync_business_permissions():
    """
    Crea los permisos específicos del SGSI y los sincroniza
    con los roles existentes.

    Puede ejecutarse repetidamente sin duplicar registros.
    """

    permission_map = {}

    created_count = 0
    existing_count = 0

    for object_ref, definitions in BUSINESS_PERMISSIONS.items():
        app_label, model_name = object_ref.split(".", 1)

        content_type = ContentType.objects.get(
            app_label=app_label,
            model=model_name,
        )

        for codename, name in definitions:
            permission, created = Permission.objects.update_or_create(
                content_type=content_type,
                codename=codename,
                defaults={
                    "name": name,
                },
            )

            permission_map[f"{app_label}.{codename}"] = permission

            if created:
                created_count += 1
            else:
                existing_count += 1

    all_refs = _all_permission_refs()
    all_business_permissions = list(permission_map.values())

    role_results = {}

    for role_name, configured_refs in ROLE_BUSINESS_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role_name)

        # Elimina únicamente nuestros permisos de negocio.
        # Conserva view/add/change configurados anteriormente.
        group.permissions.remove(*all_business_permissions)

        if configured_refs == {"*"}:
            wanted_refs = all_refs
        else:
            wanted_refs = configured_refs

        unknown_refs = wanted_refs - all_refs

        if unknown_refs:
            raise ValueError(
                f"Permisos desconocidos para {role_name}: "
                f"{sorted(unknown_refs)}"
            )

        permissions_to_assign = [
            permission_map[ref]
            for ref in wanted_refs
        ]

        if permissions_to_assign:
            group.permissions.add(*permissions_to_assign)

        role_results[role_name] = len(permissions_to_assign)

    return {
        "created": created_count,
        "existing": existing_count,
        "roles": role_results,
    }