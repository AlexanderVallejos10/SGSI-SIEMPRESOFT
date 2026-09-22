from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import (
    CorporateSystem,
    CorporateSystemStatus,
    SystemAccess,
    SystemAccessStatus,
    User,
    UserStatus,
)


CONTACT_SOURCE = "Registro de funciones e información de contactos.docx"
CONTACT_SOURCE_DATE = date(2025, 12, 3)

ASSIGNMENT_SOURCE = "04 - Registro de asignación de nuevo rol_ksalazar.pdf"
RETURN_SOURCE = "05 - Registro de devolución_lardiles.pdf"


REAL_USERS = [
    {
        "business_code": "USR-MIG-001",
        "username": "mguevara",
        "email": "mguevara@siempresoft.com",
        "first_name": "Milton",
        "last_name": "Guevara",
        "position": "Gerente General",
        "status": UserStatus.UNKNOWN,
        "status_as_of": CONTACT_SOURCE_DATE,
        "source_document": CONTACT_SOURCE,
        "source_reference": (
            'Tabla "Para el departamento de TI"; '
            "archivo modificado el 03/12/2025."
        ),
    },
    {
        "business_code": "USR-MIG-002",
        "username": "dvilela",
        "email": "dvilela@siempresoft.com",
        "first_name": "Danae",
        "last_name": "Vilela",
        "position": "Jefe de Help Desk",
        "status": UserStatus.UNKNOWN,
        "status_as_of": CONTACT_SOURCE_DATE,
        "source_document": CONTACT_SOURCE,
        "source_reference": (
            'Tabla "Para el departamento de TI"; '
            "archivo modificado el 03/12/2025."
        ),
    },
    {
        "business_code": "USR-MIG-003",
        "username": "emondragon",
        "email": "emondragon@siempresoft.com",
        "first_name": "Elio",
        "last_name": "Mondragón",
        "position": "Asistente de Producción",
        "status": UserStatus.UNKNOWN,
        "status_as_of": CONTACT_SOURCE_DATE,
        "source_document": CONTACT_SOURCE,
        "source_reference": (
            'Tabla "Para el departamento de TI"; '
            "archivo modificado el 03/12/2025."
        ),
    },
    {
        "business_code": "USR-MIG-004",
        "username": "ksalazar",
        "email": "ksalazar@siempresoft.com",
        "first_name": "Karim",
        "last_name": "Salazar",
        "position": "Oficial de seguridad de la información",
        "status": UserStatus.UNKNOWN,
        "status_as_of": CONTACT_SOURCE_DATE,
        "source_document": (
            f"{CONTACT_SOURCE}; {ASSIGNMENT_SOURCE}"
        ),
        "source_reference": (
            "El registro de contactos contiene una variante ortográfica "
            "del correo; ksalazar@siempresoft.com queda corroborado en "
            "la evidencia de correo de asignación de rol."
        ),
    },
    {
        "business_code": "USR-MIG-005",
        "username": "abaldarrago",
        "email": "abaldarrago@siempresoft.com",
        "first_name": "Andrés",
        "last_name": "Baldárrago",
        "position": "Jefe de Control de Calidad",
        "status": UserStatus.UNKNOWN,
        "status_as_of": CONTACT_SOURCE_DATE,
        "source_document": CONTACT_SOURCE,
        "source_reference": (
            'Tabla "Para el departamento de TI"; '
            "archivo modificado el 03/12/2025."
        ),
    },
    {
        "business_code": "USR-MIG-006",
        "username": "mvassallo",
        "email": "mvassallo@siempresoft.com",
        "first_name": "Marcelo",
        "last_name": "Vassallo",
        "position": "Coordinador de Desarrollo",
        "status": UserStatus.UNKNOWN,
        "status_as_of": CONTACT_SOURCE_DATE,
        "source_document": CONTACT_SOURCE,
        "source_reference": (
            'Tabla "Para el departamento de TI"; '
            "archivo modificado el 03/12/2025."
        ),
    },
    {
        "business_code": "USR-MIG-007",
        "username": "fespinoza",
        "email": "fespinoza@siempresoft.com",
        "first_name": "Fidel",
        "last_name": "Espinoza",
        "position": "Jefe de Ventas",
        "status": UserStatus.UNKNOWN,
        "status_as_of": CONTACT_SOURCE_DATE,
        "source_document": CONTACT_SOURCE,
        "source_reference": (
            'Tabla "Otras actividades de la empresa"; '
            "archivo modificado el 03/12/2025."
        ),
    },
    {
        "business_code": "USR-HIST-001",
        "username": "lardiles",
        "email": "lardiles@siempresoft.com",
        "first_name": "Lucy",
        "last_name": "Ardiles Ugaz",
        "position": "Asistente Administrativo",
        "status": UserStatus.UNKNOWN,
        "status_as_of": date(2022, 9, 1),
        "source_document": RETURN_SOURCE,
        "source_reference": (
            "Cadena de correos del 31/08/2022 y 01/09/2022 "
            "sobre devolución de activos y retiro de accesos."
        ),
    },
]


EVIDENCE_ONLY_SYSTEMS = [
    {
        "business_code": "SYS-040",
        "name": "Portal de Computrabajo",
        "status": CorporateSystemStatus.UNKNOWN,
        "status_as_of": date(2022, 9, 1),
        "source_document": RETURN_SOURCE,
        "source_reference": (
            "Correo del 31/08/2022: figura entre los permisos "
            "otorgados a Lucy Ardiles; al 01/09/2022 aparece "
            "pendiente de retirar."
        ),
    },
    {
        "business_code": "SYS-041",
        "name": "Cuenta Udemy cursos@siempresoft.com",
        "status": CorporateSystemStatus.UNKNOWN,
        "status_as_of": date(2022, 9, 1),
        "source_document": RETURN_SOURCE,
        "source_reference": (
            "Correo del 01/09/2022: cuenta compartida Udemy "
            "pendiente de cambio de contraseña."
        ),
    },
]


# Access rows intentionally preserve the state supported by evidence at the
# stated date. They must not be interpreted as the current state in 2026.
REAL_ACCESSES = [
    {
        "business_code": "ACC-HIST-001",
        "user_username": "ksalazar",
        "system_code": "SYS-016",
        "role_profile": "Administrador de SharePoint",
        "access_level": "Administrador",
        "is_privileged": True,
        "mfa_enabled": None,
        "authorization_date": date(2022, 2, 4),
        "approved_by_username": "mguevara",
        "approval_reference": (
            "Correo de Milton Guevara a Karim Salazar, "
            "04/02/2022 16:15."
        ),
        "status": SystemAccessStatus.ACTIVE,
        "status_as_of": date(2022, 2, 4),
        "notes": (
            "Asignación histórica confirmada por correo. "
            "El estado ACTIVE corresponde al 04/02/2022 y no "
            "afirma vigencia actual."
        ),
        "source_document": ASSIGNMENT_SOURCE,
        "source_reference": (
            'Asunto: Asignación de rol "Administrador de Sharepoint".'
        ),
    },

    # Lucy Ardiles: accesos informados como retirados al 01/09/2022.
    {
        "business_code": "ACC-HIST-002",
        "user_username": "lardiles",
        "system_code": "SYS-035",
        "status": SystemAccessStatus.REVOKED,
        "status_as_of": date(2022, 9, 1),
        "notes": (
            "Microsoft 365 Empresa Premium fue informado como RETIRADO "
            "en correo del 01/09/2022. La hora exacta de revocación "
            "no consta en la evidencia."
        ),
    },
    {
        "business_code": "ACC-HIST-003",
        "user_username": "lardiles",
        "system_code": "SYS-016",
        "status": SystemAccessStatus.REVOKED,
        "status_as_of": date(2022, 9, 1),
        "notes": (
            "El correo del 01/09/2022 incluye el Repositorio online "
            "de Siempresoft dentro del acceso Microsoft 365 informado "
            "como RETIRADO."
        ),
    },
    {
        "business_code": "ACC-HIST-004",
        "user_username": "lardiles",
        "system_code": "SYS-012",
        "status": SystemAccessStatus.REVOKED,
        "status_as_of": date(2022, 9, 1),
        "notes": (
            "Cuenta en el Sistema Operativo de la PC asignada para "
            "teletrabajo informada como RETIRADA el 01/09/2022."
        ),
    },
    {
        "business_code": "ACC-HIST-005",
        "user_username": "lardiles",
        "system_code": "SYS-001",
        "status": SystemAccessStatus.REVOKED,
        "status_as_of": date(2022, 9, 1),
        "notes": (
            "Portal Azure - descarga de facturas: el correo del "
            "01/09/2022 indica que ya no figuraba la cuenta de usuario."
        ),
    },
    {
        "business_code": "ACC-HIST-006",
        "user_username": "lardiles",
        "system_code": "SYS-020",
        "status": SystemAccessStatus.REVOKED,
        "status_as_of": date(2022, 9, 1),
        "notes": (
            "Sistema web Back Office informado como RETIRADO "
            "el 01/09/2022."
        ),
    },

    # Lucy Ardiles: el 01/09/2022 la evidencia todavía no confirma
    # la revocación total de los siguientes accesos.
    {
        "business_code": "ACC-HIST-007",
        "user_username": "lardiles",
        "system_code": "SYS-004",
        "status": SystemAccessStatus.UNKNOWN,
        "status_as_of": date(2022, 9, 1),
        "notes": "SIEMPRESOFT ERP figuraba pendiente de retirar.",
    },
    {
        "business_code": "ACC-HIST-008",
        "user_username": "lardiles",
        "system_code": "SYS-009",
        "status": SystemAccessStatus.UNKNOWN,
        "status_as_of": date(2022, 9, 1),
        "notes": "Portal de SUNAT figuraba pendiente de retirar.",
    },
    {
        "business_code": "ACC-HIST-009",
        "user_username": "lardiles",
        "system_code": "SYS-017",
        "status": SystemAccessStatus.UNKNOWN,
        "status_as_of": date(2022, 9, 1),
        "notes": (
            "Soporte ERP figuraba pendiente/verificar. El correo "
            "indica que dependía del usuario de Azure, pero no "
            "confirma la revocación individual."
        ),
    },
    {
        "business_code": "ACC-HIST-010",
        "user_username": "lardiles",
        "system_code": "SYS-019",
        "status": SystemAccessStatus.UNKNOWN,
        "status_as_of": date(2022, 9, 1),
        "notes": (
            "Control de Licencias figuraba pendiente/verificar. "
            "La evidencia no confirma el retiro individual."
        ),
    },
    {
        "business_code": "ACC-HIST-011",
        "user_username": "lardiles",
        "system_code": "SYS-040",
        "status": SystemAccessStatus.UNKNOWN,
        "status_as_of": date(2022, 9, 1),
        "notes": "Portal de Computrabajo figuraba pendiente de retirar.",
    },
    {
        "business_code": "ACC-HIST-012",
        "user_username": "lardiles",
        "system_code": "SYS-028",
        "status": SystemAccessStatus.UNKNOWN,
        "status_as_of": date(2022, 9, 1),
        "notes": (
            "SUNAFIL figuraba pendiente de retirar al 01/09/2022. "
            "Un correo posterior del 29/09/2022 indica actualización "
            "de información de contacto, no confirma por sí solo "
            "el estado final del acceso de Lucy."
        ),
    },
    {
        "business_code": "ACC-HIST-013",
        "user_username": "lardiles",
        "system_code": "SYS-041",
        "status": SystemAccessStatus.UNKNOWN,
        "status_as_of": date(2022, 9, 1),
        "notes": (
            "Cuenta compartida Udemy cursos@siempresoft.com "
            "figuraba pendiente de cambio de contraseña."
        ),
    },
]


def find_existing_user(item):
    user = User.objects.filter(
        business_code=item["business_code"]
    ).first()
    if user:
        return user

    user = User.objects.filter(
        username__iexact=item["username"]
    ).first()
    if user:
        return user

    if item["email"]:
        return User.objects.filter(
            email__iexact=item["email"]
        ).first()

    return None


def create_or_enrich_user(item):
    user = find_existing_user(item)
    if user is None:
        user = User(
            business_code=item["business_code"],
            username=item["username"],
            email=item["email"],
            first_name=item["first_name"],
            last_name=item["last_name"],
            position=item["position"],
            status=item["status"],
            status_as_of=item["status_as_of"],
            source_document=item["source_document"],
            source_reference=item["source_reference"],
            source_verified=True,
            is_active=False,
            is_staff=False,
        )
        user.set_unusable_password()
        user.save()
        return user, True, []

    changed = []

    # En usuarios existentes solo completamos campos vacíos. No alteramos
    # contraseña, is_active, roles, permisos ni un estado validado después.
    safe_fill = {
        "email": item["email"],
        "first_name": item["first_name"],
        "last_name": item["last_name"],
        "position": item["position"],
        "source_document": item["source_document"],
        "source_reference": item["source_reference"],
    }

    for field, value in safe_fill.items():
        if value and not getattr(user, field):
            setattr(user, field, value)
            changed.append(field)

    if not user.source_verified:
        user.source_verified = True
        changed.append("source_verified")

    if user.status_as_of is None:
        user.status_as_of = item["status_as_of"]
        changed.append("status_as_of")

    if changed:
        user.save(update_fields=changed + ["updated_at"])

    return user, False, changed


class Command(BaseCommand):
    help = (
        "Carga usuarios y accesos históricos reales sustentados "
        "por evidencias documentales de SIEMPRESOFT."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Ejecuta todas las validaciones y operaciones, "
                "pero revierte la transacción al finalizar."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        required_catalog_codes = {
            item["system_code"]
            for item in REAL_ACCESSES
            if item["system_code"] not in {"SYS-040", "SYS-041"}
        }

        existing_catalog_codes = set(
            CorporateSystem.objects.filter(
                business_code__in=required_catalog_codes
            ).values_list("business_code", flat=True)
        )

        missing_catalog_codes = (
            required_catalog_codes - existing_catalog_codes
        )

        if missing_catalog_codes:
            raise CommandError(
                "Faltan sistemas del catálogo real: "
                + ", ".join(sorted(missing_catalog_codes))
                + ". Ejecute primero seed_real_access_catalog."
            )

        user_map = {}
        users_created = 0
        users_existing = 0

        for item in REAL_USERS:
            user, created, _ = create_or_enrich_user(item)
            user_map[item["username"]] = user

            if created:
                users_created += 1
            else:
                users_existing += 1

        systems_created = 0
        systems_updated = 0

        for item in EVIDENCE_ONLY_SYSTEMS:
            _, created = CorporateSystem.objects.update_or_create(
                business_code=item["business_code"],
                defaults={
                    "name": item["name"],
                    "category": "",
                    "description": (
                        "Recurso corporativo identificado en evidencia "
                        "histórica de gestión de accesos."
                    ),
                    "authorization_authority": "",
                    "technical_implementer": "",
                    "review_frequency": "",
                    "status": item["status"],
                    "status_as_of": item["status_as_of"],
                    "source_document": item["source_document"],
                    "source_reference": item["source_reference"],
                    "source_verified": True,
                },
            )

            if created:
                systems_created += 1
            else:
                systems_updated += 1

        accesses_created = 0
        accesses_updated = 0

        for item in REAL_ACCESSES:
            user = user_map.get(item["user_username"])
            if user is None:
                user = User.objects.get(
                    username__iexact=item["user_username"]
                )

            system = CorporateSystem.objects.get(
                business_code=item["system_code"]
            )

            approver = None
            approver_username = item.get("approved_by_username")
            if approver_username:
                approver = user_map.get(approver_username)
                if approver is None:
                    approver = User.objects.filter(
                        username__iexact=approver_username
                    ).first()

            defaults = {
                "user": user,
                "system": system,
                "role_profile": item.get("role_profile", ""),
                "access_level": item.get("access_level", ""),
                "is_privileged": item.get("is_privileged"),
                "mfa_enabled": item.get("mfa_enabled"),
                "authorization_date": item.get("authorization_date"),
                "approved_by": approver,
                "approval_reference": item.get(
                    "approval_reference",
                    "",
                ),
                "status": item["status"],
                "status_as_of": item["status_as_of"],
                "last_review_at": None,
                "next_review_at": None,
                "revoked_at": None,
                "notes": item["notes"],
                "source_document": item.get(
                    "source_document",
                    RETURN_SOURCE,
                ),
                "source_reference": item.get(
                    "source_reference",
                    (
                        "Cadena de correos 31/08/2022-01/09/2022 "
                        "sobre devolución y retiro de accesos."
                    ),
                ),
                "source_verified": True,
            }

            _, created = SystemAccess.objects.update_or_create(
                business_code=item["business_code"],
                defaults=defaults,
            )

            if created:
                accesses_created += 1
            else:
                accesses_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Importación real finalizada."
            )
        )
        self.stdout.write(
            f"Usuarios: {users_created} creados, "
            f"{users_existing} existentes/enriquecidos."
        )
        self.stdout.write(
            f"Sistemas por evidencia: {systems_created} creados, "
            f"{systems_updated} actualizados."
        )
        self.stdout.write(
            f"Accesos históricos: {accesses_created} creados, "
            f"{accesses_updated} actualizados."
        )
        self.stdout.write(
            "Nota: los estados están fechados según la evidencia y "
            "no deben interpretarse automáticamente como estado actual."
        )

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN: la transacción fue revertida; "
                    "no se guardó ningún cambio."
                )
            )
