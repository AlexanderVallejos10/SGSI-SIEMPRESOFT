from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import CorporateSystem, CorporateSystemStatus

SOURCE_DOCUMENT = "Política de Control de Acceso V0.20 - 30/11/2025"

REAL_SYSTEMS = [
    {
        'business_code': 'SYS-001',
        'name': 'Portal de Azure y recursos',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Gerente General y Jefe de Producción a través del portal web de Azure.',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-002',
        'name': 'Sistemas operativos de máquinas virtuales de producción',
        'authorization_authority': 'Jefe de Producción',
        'technical_implementer': 'El Asistente de Producción a través de la gestión de usuarios de Sistemas Operativos en cada máquina virtual.',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-003',
        'name': 'Servicios de bases de datos en cada máquina virtual de producción',
        'authorization_authority': 'Jefe de Producción',
        'technical_implementer': 'El Asistente de Producción a través del SQL Server Management Studio.',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-004',
        'name': 'Sistema SIEMPRESOFT ERP',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Asistente Administrativo a través de la opción de menú Administración > Usuarios.',
        'review_frequency': 'A la última semana de cada trimestre',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-005',
        'name': 'Portal Telecrédito',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR',
    },
    {
        'business_code': 'SYS-006',
        'name': 'CPanel HostGator',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Asistente de Producción a través del portal web CPanel HostGator.',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-007',
        'name': 'Dominio GoDaddy',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Gerente General a través del Portal.',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.5 Gestión de privilegios; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-008',
        'name': 'Aplicativos Móviles (Google console)',
        'authorization_authority': 'Jefe de Producción',
        'technical_implementer': '',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.5 Gestión de privilegios',
    },
    {
        'business_code': 'SYS-009',
        'name': 'Portal de SUNAT',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Gerente General a través del Portal.',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-010',
        'name': 'Sistemas internos de dispositivo de lector de huellas',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Asistente Administrativo a través del sistema embebido del dispositivo lector.',
        'review_frequency': 'A la última semana de cada cuatrimestre (en trabajo presencial)',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-011',
        'name': 'Firewall en oficina principal',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Asistente de Producción a través del programa winbox.',
        'review_frequency': 'Cada primera semana del mes (en trabajo presencial)',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-012',
        'name': 'Sistema Operativo de PC asignada para trabajo en Oficina Principal o tele-trabajo',
        'authorization_authority': 'Jefe de Producción',
        'technical_implementer': 'El Jefe de Producción a través del portal Intune.',
        'review_frequency': 'Cada primera semana del bimestre',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-013',
        'name': 'Centro de administración de Microsoft 365',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR',
    },
    {
        'business_code': 'SYS-014',
        'name': 'Centro de seguridad de Microsoft 365 Defender',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR',
    },
    {
        'business_code': 'SYS-015',
        'name': 'Centro de administración de Microsoft Intune',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR',
    },
    {
        'business_code': 'SYS-016',
        'name': 'Sitio de Repositorio online de Siempresoft',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Oficial de seguridad de la información a través de Sharepoint.',
        'review_frequency': 'Cada término de contrato o cambio de puesto',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-017',
        'name': 'Sistema web SOPORTE ERP',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Asistente de Producción a través del SQL Server Management Studio.',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-018',
        'name': 'Azure DevOps',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Gerente General a través del portal web.',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-019',
        'name': 'Portal Control de Licencias SIEMPRESOFT ERP',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Asistente de Producción a través del SQL Server Management Studio.',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-020',
        'name': 'Sistema web Back Office',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Jefe de Producción a través del portal web en la opción Mantenimiento y Asignar acceso de los menús Accesos Web, Accesos ERP, Proceso de envío de FE y Gestión de marcas.',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-021',
        'name': 'Sistema web SIEMPRESOFT OSE de uso interno',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR',
    },
    {
        'business_code': 'SYS-022',
        'name': 'Azure CosmosDB',
        'authorization_authority': 'Jefe de Producción',
        'technical_implementer': '',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas',
    },
    {
        'business_code': 'SYS-023',
        'name': 'Azure Synapse Analytics',
        'authorization_authority': 'Jefe de Producción',
        'technical_implementer': '',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas',
    },
    {
        'business_code': 'SYS-024',
        'name': 'Azure Functions',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.7 Revisiones periódicas',
    },
    {
        'business_code': 'SYS-025',
        'name': 'Azure Storage',
        'authorization_authority': 'Jefe de Producción',
        'technical_implementer': '',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas',
    },
    {
        'business_code': 'SYS-026',
        'name': 'Azure KeyVault',
        'authorization_authority': 'Gerente General',
        'technical_implementer': '',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas',
    },
    {
        'business_code': 'SYS-027',
        'name': 'SendGrid',
        'authorization_authority': 'Jefe de Producción',
        'technical_implementer': '',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas',
    },
    {
        'business_code': 'SYS-028',
        'name': 'Buzón electrónico (SUNAFIL)',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Asistente administrativo desde el portal de SUNAFIL en la opción Registro.',
        'review_frequency': 'A la última semana de cada trimestre',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-029',
        'name': 'ZOHO Assist',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Gerente General a través del portal de Administración.',
        'review_frequency': 'Cada término de contrato o cambio de puesto',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-030',
        'name': 'Portal web SIEMPRESOFT',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': 'Cada término de contrato o cambio de puesto',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.7 Revisiones periódicas',
    },
    {
        'business_code': 'SYS-031',
        'name': 'Google Plataform',
        'authorization_authority': 'Gerente General',
        'technical_implementer': 'El Gerente General a través del portal de Administración.',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.2 Perfil ADMINISTRADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-032',
        'name': 'Portal de administración de Google',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': '',
        'source_reference': '3.2 Perfil ADMINISTRADOR',
    },
    {
        'business_code': 'SYS-033',
        'name': 'Sistema SIEMPRESOFT ERP con el ambiente de los clientes',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': '',
        'source_reference': '3.3 Perfil OPERADOR',
    },
    {
        'business_code': 'SYS-034',
        'name': 'Azure Storage Explorer',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': '',
        'source_reference': '3.3 Perfil OPERADOR',
    },
    {
        'business_code': 'SYS-035',
        'name': 'Aplicaciones de Microsoft 365 Empresa Premium',
        'authorization_authority': '',
        'technical_implementer': 'El Gerente General a través del portal web de Microsoft 365 Empresa Premium',
        'review_frequency': '',
        'source_reference': '3.3 Perfil OPERADOR; 3.9 Implementación técnica',
    },
    {
        'business_code': 'SYS-036',
        'name': 'Azure Front Door',
        'authorization_authority': 'Gerente General',
        'technical_implementer': '',
        'review_frequency': 'Cada primera semana del mes.',
        'source_reference': '3.3 Perfil OPERADOR; 3.5 Gestión de privilegios; 3.7 Revisiones periódicas',
    },
    {
        'business_code': 'SYS-037',
        'name': 'NotebookLM',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': '',
        'source_reference': '3.3 Perfil OPERADOR',
    },
    {
        'business_code': 'SYS-038',
        'name': 'Portal de licencias para Sistema Operativo Windows',
        'authorization_authority': '',
        'technical_implementer': '',
        'review_frequency': 'Cada primera semana del mes',
        'source_reference': '3.7 Revisiones periódicas',
    },
    {
        'business_code': 'SYS-039',
        'name': 'Azure AD Premium Plan 2',
        'authorization_authority': '',
        'technical_implementer': 'El Gerente General a través del Portal de Azure / Licencias.',
        'review_frequency': '',
        'source_reference': '3.9 Implementación técnica',
    },
]


class Command(BaseCommand):
    help = "Carga o actualiza el catálogo real de sistemas corporativos desde la Política de Control de Acceso vigente"

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for item in REAL_SYSTEMS:
            _, created = CorporateSystem.objects.update_or_create(
                business_code=item["business_code"],
                defaults={
                    "name": item["name"],
                    "category": "",
                    "description": "",
                    "authorization_authority": item["authorization_authority"],
                    "technical_implementer": item["technical_implementer"],
                    "review_frequency": item["review_frequency"],
                    "status": CorporateSystemStatus.ACTIVE,
                    "source_document": SOURCE_DOCUMENT,
                    "source_reference": item["source_reference"],
                    "source_verified": True,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogo real sincronizado: {created_count} creados, {updated_count} actualizados, {len(REAL_SYSTEMS)} total."
            )
        )