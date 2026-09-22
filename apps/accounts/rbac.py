from django.contrib.auth.models import Group, Permission
from django.db import transaction


# ============================================================
# RBAC ESTÁNDAR POR MODELO
# ============================================================
#
# IMPORTANTE:
#
# Ya no damos permisos por aplicación completa.
#
# Cada rol recibe permisos sobre modelos concretos.
#
# Esto evita que al agregar modelos nuevos a "accounts"
# un rol reciba permisos automáticamente.
#
# No asignamos ningún delete_*.
# ============================================================


ROLE_MODEL_RULES = {

    # --------------------------------------------------------
    # ADMINISTRADOR SGSI
    # --------------------------------------------------------

    "Administrador SGSI": {

        "accounts.user": {
            "view",
            "add",
            "change",
        },

        "accounts.corporatesystem": {
            "view",
            "add",
            "change",
        },

        "accounts.systemaccess": {
            "view",
            "add",
            "change",
        },

        "accounts.accessreview": {
            "view",
            "add",
            "change",
        },

        "documents.document": {
            "view",
            "add",
            "change",
        },

        "documents.documentversion": {
            "view",
            "add",
            "change",
        },

        "documents.evidence": {
            "view",
            "add",
            "change",
        },

        "controls.controlframework": {
            "view",
            "add",
            "change",
        },

        "controls.control": {
            "view",
            "add",
            "change",
        },

        "controls.controlevidence": {
            "view",
            "add",
            "change",
        },

        "assets.asset": {
            "view",
            "add",
            "change",
        },

        "assets.assetmovement": {
            "view",
            "add",
            "change",
        },

        "assets.maintenance": {
            "view",
            "add",
            "change",
        },

        "risks.risk": {
            "view",
            "add",
            "change",
        },

        "risks.riskassessment": {
            "view",
            "add",
            "change",
        },

        "risks.risktreatment": {
            "view",
            "add",
            "change",
        },

        "incidents.incident": {
            "view",
            "add",
            "change",
        },

        "incidents.incidentevent": {
            "view",
            "add",
            "change",
        },

        "incidents.vulnerability": {
            "view",
            "add",
            "change",
        },

        "assurance.audit": {
            "view",
            "add",
            "change",
        },

        "assurance.finding": {
            "view",
            "add",
            "change",
        },

        "assurance.improvementaction": {
            "view",
            "add",
            "change",
        },

        "auditlog.auditlog": {
            "view",
        },
    },


    # --------------------------------------------------------
    # OFICIAL DE SEGURIDAD
    # --------------------------------------------------------

    "Oficial de Seguridad de la Información": {

        "accounts.user": {
            "view",
        },

        "accounts.corporatesystem": {
            "view",
        },

        "accounts.systemaccess": {
            "view",
            "add",
            "change",
        },

        "accounts.accessreview": {
            "view",
            "add",
            "change",
        },

        "documents.document": {
            "view",
            "add",
            "change",
        },

        "documents.documentversion": {
            "view",
            "add",
            "change",
        },

        "documents.evidence": {
            "view",
            "add",
            "change",
        },

        "controls.controlframework": {
            "view",
            "add",
            "change",
        },

        "controls.control": {
            "view",
            "add",
            "change",
        },

        "controls.controlevidence": {
            "view",
            "add",
            "change",
        },

        "assets.asset": {
            "view",
        },

        "assets.assetmovement": {
            "view",
        },

        "assets.maintenance": {
            "view",
        },

        "risks.risk": {
            "view",
            "add",
            "change",
        },

        "risks.riskassessment": {
            "view",
            "add",
            "change",
        },

        "risks.risktreatment": {
            "view",
            "add",
            "change",
        },

        "incidents.incident": {
            "view",
            "add",
            "change",
        },

        "incidents.incidentevent": {
            "view",
            "add",
            "change",
        },

        "incidents.vulnerability": {
            "view",
            "add",
            "change",
        },

        "assurance.audit": {
            "view",
            "add",
            "change",
        },

        "assurance.finding": {
            "view",
            "add",
            "change",
        },

        "assurance.improvementaction": {
            "view",
            "add",
            "change",
        },

        "auditlog.auditlog": {
            "view",
        },
    },


    # --------------------------------------------------------
    # ALTA DIRECCIÓN
    # --------------------------------------------------------

    "Alta Dirección": {

        "documents.document": {"view"},
        "documents.documentversion": {"view"},
        "documents.evidence": {"view"},

        "controls.controlframework": {"view"},
        "controls.control": {"view"},
        "controls.controlevidence": {"view"},

        "assets.asset": {"view"},
        "assets.assetmovement": {"view"},
        "assets.maintenance": {"view"},

        "risks.risk": {"view"},
        "risks.riskassessment": {"view"},
        "risks.risktreatment": {"view"},

        "incidents.incident": {"view"},
        "incidents.incidentevent": {"view"},
        "incidents.vulnerability": {"view"},

        "assurance.audit": {"view"},
        "assurance.finding": {"view"},
        "assurance.improvementaction": {"view"},
    },


    # --------------------------------------------------------
    # RESPONSABLE TI
    # --------------------------------------------------------

    "Responsable TI": {

        "accounts.user": {
            "view",
        },

        "accounts.corporatesystem": {
            "view",
            "add",
            "change",
        },

        "accounts.systemaccess": {
            "view",
            "add",
            "change",
        },

        "accounts.accessreview": {
            "view",
            "add",
            "change",
        },

        "documents.document": {"view"},
        "documents.documentversion": {"view"},
        "documents.evidence": {"view"},

        "controls.controlframework": {"view"},
        "controls.control": {"view"},
        "controls.controlevidence": {"view"},

        "assets.asset": {
            "view",
            "add",
            "change",
        },

        "assets.assetmovement": {
            "view",
            "add",
            "change",
        },

        "assets.maintenance": {
            "view",
            "add",
            "change",
        },

        "risks.risk": {"view"},
        "risks.riskassessment": {"view"},
        "risks.risktreatment": {"view"},

        "incidents.incident": {
            "view",
            "add",
            "change",
        },

        "incidents.incidentevent": {
            "view",
            "add",
            "change",
        },

        "incidents.vulnerability": {
            "view",
            "add",
            "change",
        },
    },


    # --------------------------------------------------------
    # RECURSOS HUMANOS
    # --------------------------------------------------------

    "Recursos Humanos": {

        "accounts.user": {
            "view",
            "add",
            "change",
        },

        "accounts.corporatesystem": {
            "view",
        },

        "accounts.systemaccess": {
            "view",
        },

        "accounts.accessreview": {
            "view",
        },

        "assets.asset": {"view"},
        "assets.assetmovement": {"view"},
        "assets.maintenance": {"view"},

        "documents.document": {"view"},
        "documents.documentversion": {"view"},
        "documents.evidence": {"view"},
    },


    # --------------------------------------------------------
    # RESPONSABLE DE ACTIVOS
    # --------------------------------------------------------

    "Responsable de Activos": {

        "accounts.user": {
            "view",
        },

        "assets.asset": {
            "view",
            "add",
            "change",
        },

        "assets.assetmovement": {
            "view",
            "add",
            "change",
        },

        "assets.maintenance": {
            "view",
            "add",
            "change",
        },

        "documents.document": {"view"},
        "documents.documentversion": {"view"},
        "documents.evidence": {"view"},
    },


    # --------------------------------------------------------
    # PROPIETARIO DE RIESGO
    # --------------------------------------------------------

    "Propietario de Riesgo": {

        "documents.document": {"view"},
        "documents.documentversion": {"view"},
        "documents.evidence": {"view"},

        "controls.controlframework": {"view"},
        "controls.control": {"view"},
        "controls.controlevidence": {"view"},

        "risks.risk": {
            "view",
            "add",
            "change",
        },

        "risks.riskassessment": {
            "view",
            "add",
            "change",
        },

        "risks.risktreatment": {
            "view",
            "add",
            "change",
        },

        "incidents.incident": {"view"},
        "incidents.incidentevent": {"view"},
        "incidents.vulnerability": {"view"},
    },


    # --------------------------------------------------------
    # RESPONSABLE DE CONTROL
    # --------------------------------------------------------

    "Responsable de Control": {

        "documents.document": {
            "view",
            "add",
            "change",
        },

        "documents.documentversion": {
            "view",
            "add",
            "change",
        },

        "documents.evidence": {
            "view",
            "add",
            "change",
        },

        "controls.controlframework": {
            "view",
            "add",
            "change",
        },

        "controls.control": {
            "view",
            "add",
            "change",
        },

        "controls.controlevidence": {
            "view",
            "add",
            "change",
        },

        "risks.risk": {"view"},
        "risks.riskassessment": {"view"},
        "risks.risktreatment": {"view"},

        "incidents.incident": {"view"},
        "incidents.incidentevent": {"view"},
        "incidents.vulnerability": {"view"},
    },


    # --------------------------------------------------------
    # AUDITOR
    # --------------------------------------------------------

    "Auditor": {

        "accounts.user": {"view"},
        "accounts.corporatesystem": {"view"},
        "accounts.systemaccess": {"view"},
        "accounts.accessreview": {"view"},

        "documents.document": {"view"},
        "documents.documentversion": {"view"},
        "documents.evidence": {"view"},

        "controls.controlframework": {"view"},
        "controls.control": {"view"},
        "controls.controlevidence": {"view"},

        "assets.asset": {"view"},
        "assets.assetmovement": {"view"},
        "assets.maintenance": {"view"},

        "risks.risk": {"view"},
        "risks.riskassessment": {"view"},
        "risks.risktreatment": {"view"},

        "incidents.incident": {"view"},
        "incidents.incidentevent": {"view"},
        "incidents.vulnerability": {"view"},

        "assurance.audit": {
            "view",
            "add",
            "change",
        },

        "assurance.finding": {
            "view",
            "add",
            "change",
        },

        "assurance.improvementaction": {
            "view",
            "add",
            "change",
        },

        "auditlog.auditlog": {"view"},
    },


    # --------------------------------------------------------
    # RESPONSABLE DOCUMENTAL
    # --------------------------------------------------------

    "Responsable Documental": {

        "accounts.user": {"view"},

        "documents.document": {
            "view",
            "add",
            "change",
        },

        "documents.documentversion": {
            "view",
            "add",
            "change",
        },

        "documents.evidence": {
            "view",
            "add",
            "change",
        },

        "controls.controlframework": {"view"},
        "controls.control": {"view"},
        "controls.controlevidence": {"view"},
    },


    # --------------------------------------------------------
    # USUARIO / COLABORADOR
    # --------------------------------------------------------

    "Usuario / Colaborador": {

        "documents.document": {"view"},
        "documents.documentversion": {"view"},
        "documents.evidence": {"view"},

        "controls.controlframework": {"view"},
        "controls.control": {"view"},
        "controls.controlevidence": {"view"},

        "assets.asset": {"view"},
        "assets.assetmovement": {"view"},
        "assets.maintenance": {"view"},

        "risks.risk": {"view"},
        "risks.riskassessment": {"view"},
        "risks.risktreatment": {"view"},

        "incidents.incident": {"view"},
        "incidents.incidentevent": {"view"},
        "incidents.vulnerability": {"view"},
    },


    # --------------------------------------------------------
    # CONSULTA / LECTOR
    # --------------------------------------------------------

    "Consulta / Lector": {

        "documents.document": {"view"},
        "documents.documentversion": {"view"},
        "documents.evidence": {"view"},

        "controls.controlframework": {"view"},
        "controls.control": {"view"},
        "controls.controlevidence": {"view"},

        "risks.risk": {"view"},
        "risks.riskassessment": {"view"},
        "risks.risktreatment": {"view"},

        "assurance.audit": {"view"},
        "assurance.finding": {"view"},
        "assurance.improvementaction": {"view"},
    },
}


STANDARD_ACTIONS = {
    "view",
    "add",
    "change",
    "delete",
}


def _split_model_ref(model_ref):
    return model_ref.split(".", 1)


def _get_standard_permission(
    app_label,
    model_name,
    action,
):
    codename = f"{action}_{model_name}"

    return Permission.objects.filter(
        content_type__app_label=app_label,
        content_type__model=model_name,
        codename=codename,
    ).first()


def _managed_model_refs():
    refs = set()

    for model_rules in ROLE_MODEL_RULES.values():
        refs.update(model_rules.keys())

    return refs


def _managed_standard_permissions():
    permissions = []

    for model_ref in _managed_model_refs():
        app_label, model_name = (
            _split_model_ref(model_ref)
        )

        for action in STANDARD_ACTIONS:
            permission = _get_standard_permission(
                app_label,
                model_name,
                action,
            )

            if permission is not None:
                permissions.append(permission)

    return permissions


@transaction.atomic
def sync_rbac_roles():
    """
    Sincroniza permisos estándar Django por MODELO.

    IMPORTANTE:

    Solo elimina y reconstruye permisos estándar
    view/add/change/delete de los modelos gestionados.

    Los permisos específicos de negocio, como:

        assets.assign_asset
        risks.close_risk
        documents.publish_document

    se conservan intactos.
    """

    managed_permissions = (
        _managed_standard_permissions()
    )

    results = {}

    for role_name, model_rules in (
        ROLE_MODEL_RULES.items()
    ):
        group, _ = Group.objects.get_or_create(
            name=role_name
        )

        # Elimina únicamente permisos estándar
        # administrados por este RBAC.
        #
        # NO elimina permisos de negocio.
        if managed_permissions:
            group.permissions.remove(
                *managed_permissions
            )

        desired_permissions = []

        for model_ref, actions in (
            model_rules.items()
        ):
            app_label, model_name = (
                _split_model_ref(model_ref)
            )

            for action in actions:
                if action == "delete":
                    raise ValueError(
                        "Los roles funcionales del "
                        "SGSI no pueden recibir "
                        "permisos delete_*."
                    )

                permission = (
                    _get_standard_permission(
                        app_label,
                        model_name,
                        action,
                    )
                )

                if permission is None:
                    raise ValueError(
                        "No existe el permiso "
                        f"{app_label}."
                        f"{action}_{model_name}"
                    )

                desired_permissions.append(
                    permission
                )

        if desired_permissions:
            group.permissions.add(
                *desired_permissions
            )

        results[role_name] = len(
            desired_permissions
        )

    return results