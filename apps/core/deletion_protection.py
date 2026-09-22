from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete
from django.dispatch import receiver


PROTECTED_MODEL_LABELS = frozenset(
    {
        # Usuarios
        "accounts.user",
	"accounts.corporatesystem",
	"accounts.systemaccess",
	"accounts.accessreview",

        # Documentos, estructura SGSI y evidencias
	"documents.document",
	"documents.documentversion",
	"documents.evidence",
	"documents.sgsisection",
	"documents.sourceartifact",
        "documents.sourcepackage",
        "documents.sourceartifactclassification",
        "documents.documentversionrepresentation",
        "documents.documentimportissue",
        "documents.documentsectionassignment",

        # Controles
        "controls.controlframework",
        "controls.control",
        "controls.controlevidence",
        "controls.isoclause",
        "controls.isorequirement",
        "controls.controlsupportreference",
        "controls.isodataqualityissue",
        "controls.controldocumentassignment",

        # Dashboard SGSI
        "dashboard.dashboardsnapshot",
        "dashboard.dashboardsourcerow",
        "dashboard.sgsimetric",
        "dashboard.securityobjective",
        "dashboard.objectivealignment",
        "dashboard.strategicfactor",

        # Organización
        "organization.organizationalarea",
        "organization.position",
        "organization.positionassignment",

        # SGSI 4.1
        "context41.contextdocument",
        "context41.contextdocumentversion",
        "context41.legalrequirement",

        # Activos
        "assets.asset",
        "assets.assetmovement",
        "assets.maintenance",

        # Riesgos
        "risks.risk",
        "risks.riskassessment",
        "risks.risktreatment",

        # Incidentes y vulnerabilidades
        "incidents.incident",
        "incidents.incidentevent",
        "incidents.vulnerability",

        # Auditoría y mejora
        "assurance.audit",
        "assurance.finding",
        "assurance.improvementaction",

        # Bitácora
        "auditlog.auditlog",
    }
)


# Elimina la acción masiva "Eliminar seleccionados"
# del Django Admin.
admin.site.disable_action("delete_selected")


@receiver(
    pre_delete,
    dispatch_uid="sgsi_block_physical_deletion",
)
def block_physical_deletion(sender, instance, **kwargs):
    """
    Impide la eliminación física de los objetos principales del SGSI.

    Los registros deben cambiar de estado:
    cerrado, inactivo, obsoleto, archivado, etc.
    """

    model_label = sender._meta.label_lower

    if model_label not in PROTECTED_MODEL_LABELS:
        return

    raise PermissionDenied(
        "La eliminación física está bloqueada para "
        f"'{sender._meta.verbose_name}'. "
        "Utilice el flujo funcional de cierre, "
        "desactivación, obsolescencia o archivado."
    )