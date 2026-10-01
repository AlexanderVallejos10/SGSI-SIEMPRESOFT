import tempfile
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.assets.models import Asset
from apps.assurance.models import Audit, Finding
from apps.core.testing import ACTIVOS, DOCUMENTOS, MATRIZ_2026, REGISTROS, requiere_datos_reales
from apps.dashboard.manual_documents import resolve
from apps.documents.models import Document
from apps.incidents.models import Incident, Vulnerability
from apps.organization.models import PositionAssignment

PASOS = ["datos", "unificar", "organigrama", "documentos", "riesgos", "incidentes", "auditorias", "vulnerabilidades"]


@requiere_datos_reales(ACTIVOS, REGISTROS, DOCUMENTOS, MATRIZ_2026)
@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="sgsi-test-media-"))
class CargaTotalDeSiempresoft(TestCase):
    """Ejecuta cargar_todo_siempresoft con los datos reales sobre una base con el organigrama por defecto."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username="carga-admin", business_code="T-CARGA", is_superuser=True)
        # Un colaborador que ya estaba registrado con su propio código: ese código debe mandar.
        cls.jose = User.objects.create_user(username="jose.torres", business_code="EMP-007", first_name="José",
                                            last_name="Torres", email="jtorres@siempresoft.com")
        call_command("seed_organization_chart", apply=True, stdout=StringIO())
        call_command("cargar_todo_siempresoft", paso=PASOS, stdout=StringIO())

    def test_el_colaborador_existente_manda_y_no_se_duplica(self):
        User = get_user_model()
        self.assertEqual(User.objects.filter(email__iexact="jtorres@siempresoft.com").count(), 1)
        self.assertFalse(User.objects.filter(business_code="COL-JTORRES").exists())
        self.jose.refresh_from_db()
        self.assertEqual(self.jose.business_code, "EMP-007")
        self.assertTrue(Asset.objects.filter(custodian=self.jose).exists())  # su laptop SS1-LAP-016 de 2026

    def test_documentos_del_manual_ya_no_faltan(self):
        for name in ("Política de Seguridad de la Información", "Metodología para la evaluación y tratamiento de Riesgos",
                     "Declaración de Aplicabilidad", "Procedimiento para auditoría interna",
                     "Procedimiento para medidas correctivas preventivas y de mejora"):
            with self.subTest(name=name):
                self.assertTrue(resolve(name)["found"])
        policy = Document.objects.get(title="Política de Seguridad de la Información")
        self.assertTrue(policy.versions.filter(version="0.12").exists())
        # Los numerales (3.1, 5.2, …) se enlazan si existen; en la base de pruebas no se crean.
        from apps.documents.models import SGSISection
        if SGSISection.objects.filter(code="5.2").exists():
            self.assertTrue(policy.sgsi_sections.filter(code="5.2").exists())

    def test_organigrama_con_colaboradores_reales(self):
        gerente = PositionAssignment.objects.filter(position__title="Gerente General", end_date__isnull=True).first()
        self.assertIsNotNone(gerente)
        self.assertEqual(gerente.user.email, "mguevara@siempresoft.com")
        self.assertTrue(PositionAssignment.objects.filter(position__title="Desarrolladores", end_date__isnull=True).count() >= 2)

    def test_incidentes_auditorias_y_vulnerabilidades(self):
        self.assertEqual(Incident.objects.count(), 93)
        self.assertEqual(Audit.objects.count(), 35)
        # 208 filas de auditoría en el registro, pero 4 hallazgos de 2025 están repetidos: 204 hallazgos distintos.
        self.assertEqual(Finding.objects.count(), 204)
        repeated = Finding.objects.filter(description__contains="figura 2 veces con estados distintos")
        self.assertEqual(repeated.count(), 4)
        self.assertFalse(repeated.filter(status="closed").exists())  # quedan abiertos hasta confirmar
        self.assertTrue(Vulnerability.objects.exists())

    def test_volver_a_ejecutar_no_duplica(self):
        User = get_user_model()
        before = (User.objects.count(), Document.objects.count(), Incident.objects.count(), Audit.objects.count(),
                  Vulnerability.objects.count(), PositionAssignment.objects.count())
        call_command("cargar_todo_siempresoft", paso=PASOS, stdout=StringIO())
        after = (User.objects.count(), Document.objects.count(), Incident.objects.count(), Audit.objects.count(),
                 Vulnerability.objects.count(), PositionAssignment.objects.count())
        self.assertEqual(before, after)
