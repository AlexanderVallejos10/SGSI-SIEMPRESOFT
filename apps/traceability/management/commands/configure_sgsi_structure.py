from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organization.models import OrganizationalArea, Position
from apps.processes.models import ProcessCategory, ProcessNode, ProcessRelation

AREAS = [
    ("SI", "Seguridad de la Información", []),
    ("CONS", "Consultoría", ["ORG-JCONS", "ORG-CONS"]),
    ("SOP", "Soporte al Cliente", ["ORG-JHD", "ORG-AHD"]),
    ("DES", "Desarrollo", ["ORG-JDES", "ORG-DES"]),
    ("PROD", "Producción", ["ORG-APROD", "ORG-PLAT"]),
    ("ADM", "Administración", ["ORG-AADM"]),
]
MAP = [
    ("PROC-RD", "Revisión por la Dirección", "strategic", 500, 74, False, True),
    ("PROC-VENTAS", "Gestión Comercial", "operational", 105, 305, True, False),
    ("PROC-OSE", "Validación de comprobantes OSE", "operational", 500, 190, True, False),
    ("PROC-SOPORTE", "Gestión del Éxito y Atención del Cliente", "operational", 500, 305, True, False),
    ("PROC-DES", "Ingeniería y Calidad de Software", "operational", 500, 420, True, False),
    ("PROC-PROD", "Gestión de Operaciones", "operational", 865, 420, True, False),
    ("PROC-RRHH", "Recursos Humanos", "support", 80, 542, True, False),
    ("PROC-FC", "Facturación y Cobranza", "support", 295, 542, True, False),
    ("PROC-LOG", "Logística", "support", 515, 542, True, False),
    ("PROC-INFRA", "Infraestructura Tecnológica", "support", 735, 542, True, False),
    ("PROC-MKT", "Marketing", "support", 950, 542, True, False),
    ("PROC-CONT", "Contabilidad", "support", 500, 630, False, True),
]


class Command(BaseCommand):
    help = "Simula configuración de áreas y mapa V0.15. --apply guarda. --map aplica distribución y relaciones de referencia, preservando procesos adicionales."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--map", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        for code, name, codes in AREAS:
            area = OrganizationalArea.objects.filter(name__iexact=name).first()
            if not area:
                area, _ = OrganizationalArea.objects.get_or_create(
                    code="AREA-" + code, defaults={"name": name}
                )
            count = 0
            for position in Position.objects.filter(code__in=codes, area__isnull=True):
                position.area = area
                position.save()
                count += 1
            self.stdout.write(f"{area.name}: {count} puestos sin área vinculados")
        if options["map"]:
            from apps.processes.models import ProcessReferenceDocument
            ProcessReferenceDocument.objects.get_or_create(kind="map", defaults={"slug":"mapa-de-procesos", "title":"Mapa de procesos SIEMPRESOFT"})
            for code, name, kind, x, y, scope, external in MAP:
                category, _ = ProcessCategory.objects.get_or_create(
                    kind=kind,
                    defaults={
                        "code": "PROC-" + kind.upper(),
                        "name": {
                            "strategic": "Procesos estratégicos",
                            "operational": "Procesos operativos",
                            "support": "Procesos de apoyo",
                        }[kind],
                    },
                )
                process, created = ProcessNode.objects.get_or_create(
                    code=code, defaults={"name": name, "category": category}
                )
                process.name = name
                process.category = category
                process.x = x
                process.y = y
                process.is_in_scope = scope
                process.is_external = external
                process.save()
            # The older reference included Consultoría as a process. Preserve it outside this PDF layout.
            for process in ProcessNode.objects.filter(code="PROC-CONS"):
                process.is_active = False
                process.save()
            codes = [r[0] for r in MAP] + ["PROC-CONS"]
            for relation in ProcessRelation.objects.filter(source__code__in=codes, target__code__in=codes):
                relation.is_active = False
                relation.save()
            for source, target in [
                ("PROC-VENTAS", "PROC-SOPORTE"),
                ("PROC-SOPORTE", "PROC-OSE"),
                ("PROC-SOPORTE", "PROC-DES"),
                ("PROC-DES", "PROC-PROD"),
                ("PROC-PROD", "PROC-DES"),
            ]:
                relation, _ = ProcessRelation.objects.get_or_create(
                    source=ProcessNode.objects.get(code=source),
                    target=ProcessNode.objects.get(code=target),
                    relation_type="flow",
                )
                relation.is_active = True
                relation.save()
            for process_code, area_code in [
                ("PROC-DES", "DES"),
                ("PROC-PROD", "PROD"),
                ("PROC-OSE", "PROD"),
                ("PROC-SOPORTE", "SOP"),
                ("PROC-RRHH", "ADM"),
                ("PROC-FC", "ADM"),
                ("PROC-LOG", "ADM"),
                ("PROC-INFRA", "PROD"),
            ]:
                process = ProcessNode.objects.get(code=process_code)
                area = OrganizationalArea.objects.filter(code="AREA-" + area_code).first()
                if area and not process.primary_area_id:
                    process.primary_area = area
                    process.save()
            self.stdout.write(
                "Distribución V0.15 aplicada a los procesos de referencia; procesos adicionales conservados."
            )
        # Dedicated role avoids giving document-grant authority through edit-user permission.
        group, _ = Group.objects.get_or_create(name="Gestor de trazabilidad")
        for app in ("traceability", "organization", "processes", "risks"):
            group.permissions.add(
                *Permission.objects.filter(content_type__app_label=app).exclude(
                    codename__startswith="delete_"
                )
            )
        group.permissions.add(
            *Permission.objects.filter(content_type__app_label="accounts", codename="view_user")
        )
        self.stdout.write(
            "Rol Gestor de trazabilidad disponible; asignarlo explícitamente desde administración."
        )
        self.stdout.write(
            "Revisar cargos combinados, áreas sin puestos y procesos sin área responsable; no se infieren asignaciones ambiguas."
        )
        if not options["apply"]:
            transaction.set_rollback(True)
            self.stdout.write(
                "SIMULACIÓN: no se guardaron cambios. Use --apply para confirmar esta configuración."
            )
