"""Ajustes de la reunión con Karim: tratamiento por opción, control del Anexo A,
tipos de identificación e importación de la matriz modelo sobre la matriz 2026."""

from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from apps.controls.models import Control, ControlFramework
from apps.processes.models import ProcessCategory, ProcessNode
from apps.processes.selectors import process_payload
from apps.risks.models import RiskAssessment
from apps.risks.models import IdentificationType, Risk, RiskTreatment, TreatmentOption
from apps.traceability.importer import import_workbook
from apps.traceability.models import SourceRow

HEAD_2026 = [
    "ID", "Proceso", "Origen del riesgo", "Categoría de riesgo",
    "Fuente de riesgo (causa u origen específico)", "Evento",
    "Estado final deseado / Motivación (DES)\n(solo si el origen es deliberado)",
    "Escenario estratégico", "Consecuencia", "Probabilidad", "Nivel de riesgo",
    "Controles existentes", "Propietario del riesgo",
]
HEAD_MODELO = [
    "ID", "Proceso", "Origen del riesgo", "Categoría de riesgo",
    "Fuente de riesgo (causa u origen específico)", "Evento (que pasa tecnicamente)",
    "Estado final deseado / Motivación (DES)\n(solo si el origen es deliberado)",
    "Activo o proceso de negocio afectado", "Escenario estratégico (narrativa)",
    "Escenario operacional (condición técnica)", "Origen del hallazgo",
    "Referencia / evidencia", "Consecuencia", "Probabilidad", "Nivel de riesgo",
    "Controles existentes", "Propietario del riesgo", "¿Tiene tratamiento\nasignado?",
    "Estado del registro",
]
HEAD_TRAT = [
    "Item", "ID del riesgo", "Proceso\n(auto)", "Nivel de riesgo\n(auto)",
    "Opción de tratamiento", "Control / actividad a implementar",
    "Responsable de implementación", "Plazo inicio", "Plazo fin", "Recursos requeridos",
    "Estado de implementación", "Consecuencia residual", "Probabilidad residual",
    "Nivel de riesgo\nresidual (auto)", "Fecha de cierre", "Observaciones",
]


def workbook(name, matrix_head, rows, treatment_rows=(), treatment_head=HEAD_TRAT):
    book = Workbook()
    matrix = book.active
    matrix.title = "Matriz de riesgos"
    for _ in range(3):
        matrix.append(["título"])
    matrix.append(matrix_head)
    for row in rows:
        matrix.append(row)
    treatment = book.create_sheet("Tratamiento de riesgos")
    for _ in range(3):
        treatment.append(["título"])
    treatment.append(list(treatment_head))
    for row in treatment_rows:
        treatment.append(row)
    buffer = BytesIO()
    book.save(buffer)
    return SimpleUploadedFile(name, buffer.getvalue())


def row_2026(code, process, threat="Procesos manuales", scenario="Escenario 2026", probability="3 - Probable"):
    return [code, process, "Accidental - técnico", "Operativo", threat, "Evento 2026", "",
            scenario, "3 - Serio", probability, None, "Revisión", "Rol desconocido"]


def row_modelo(code, process, probability="4 – Muy probable"):
    return [code, process, "Técnico (falla de sistema/infraestructura)", "Operativo",
            "Procesos manuales en la web de soporte", "Solicitudes abiertas fuera de plazo",
            "No aplica", "Web de soporte al cliente", "Escenario modelo", "Cierre manual",
            "Revisión periódica", "Reportes de la web", "3 - Serio", probability, None,
            "Revisión manual", "Rol desconocido", None, None]


@override_settings(MEDIA_ROOT="/tmp/sgsi-test-media")
class AjustesKarim(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="admin-k", business_code="T-K", is_superuser=True
        )
        category = ProcessCategory.objects.create(code="OPK", name="Operativos", kind="operational")
        self.ose = ProcessNode.objects.create(code="PROC-OSE", name="Validación de comprobantes OSE", category=category)
        self.soporte = ProcessNode.objects.create(
            code="PROC-SOPORTE", name="Gestión del Éxito y Atención del Cliente", category=category
        )
        self.desarrollo = ProcessNode.objects.create(
            code="PROC-DES", name="Ingeniería y Calidad de Software", category=category
        )
        iso = ControlFramework.objects.create(code="ISO27001-2022", name="ISO/IEC 27001", version="2022")
        self.control = Control.objects.create(framework=iso, code="8.5", name="Autenticación segura")
        other = ControlFramework.objects.create(code="OTRO", name="Otro marco")
        self.foreign_control = Control.objects.create(framework=other, code="8.5", name="Ajeno")
        self.risk = Risk.objects.create(code="R90", process="Prueba", scenario="Escenario")

    def treatment(self, option, **extra):
        return RiskTreatment(risk=self.risk, option=option, action="Actividad", **extra)

    def errors(self, obj):
        with self.assertRaises(ValidationError) as ctx:
            obj.full_clean()
        return set(ctx.exception.message_dict)

    # --- Tratamiento según la opción elegida ---

    def test_eleccion_de_controles_exige_control_del_anexo_a(self):
        t = self.treatment(TreatmentOption.CONTROLS)
        self.assertIn("control", self.errors(t))
        t.control = self.control
        t.full_clean()

    def test_control_de_otro_marco_se_rechaza(self):
        t = self.treatment(TreatmentOption.CONTROLS, control=self.foreign_control)
        self.assertIn("control", self.errors(t))

    def test_transferencia_exige_tercero_responsabilidades_y_contrato(self):
        t = self.treatment(TreatmentOption.TRANSFER)
        self.assertEqual(
            self.errors(t), {"third_party", "third_party_responsibilities", "contract_reference"}
        )
        t.third_party = "Proveedor de nube"
        t.third_party_responsibilities = "Monitoreo 24/7 y respaldo diario"
        t.contract_reference = "Contrato 2026-015"
        t.full_clean()

    def test_evitar_exige_como_se_evita(self):
        t = self.treatment(TreatmentOption.AVOID)
        self.assertEqual(self.errors(t), {"avoidance_method"})
        t.avoidance_method = "Se descontinúa el uso del proceso manual."
        t.full_clean()

    def test_aceptar_exige_justificacion(self):
        t = self.treatment(TreatmentOption.ACCEPT)
        self.assertEqual(self.errors(t), {"acceptance_justification"})
        t.acceptance_justification = "Un centro de datos propio cuesta más que el riesgo."
        t.full_clean()

    def test_riesgo_de_proyecto_exige_nombre_de_proyecto(self):
        risk = Risk(code="R91", process="Prueba", scenario="S", identification_type=IdentificationType.PROJECT)
        self.assertIn("project_name", self.errors(risk))
        risk.project_name = "Migración a Azure"
        risk.full_clean()

    def test_riesgo_por_activos_exige_activo(self):
        risk = Risk(code="R92", process="Prueba", scenario="S", identification_type=IdentificationType.ASSETS)
        self.assertIn("affected_asset_text", self.errors(risk))

    # --- Importación: matriz 2026 y luego la matriz modelo de Karim ---

    def test_matriz_modelo_actualiza_ids_existentes_y_reubica_el_proceso(self):
        import_workbook(
            workbook("2026.xlsx", HEAD_2026, [row_2026("R47", "Facturación electrónica PSE")]),
            "risks", self.admin, apply=True,
        )
        risk = Risk.objects.get(code="R47")
        self.assertEqual(risk.processes.count(), 0)

        result = import_workbook(
            workbook(
                "modelo.xlsx",
                HEAD_MODELO,
                [row_modelo("R47", "Gestión del éxito y atención del cliente"), ["R60"] + [None] * 18],
            ),
            "risks", self.admin, apply=True,
        )
        self.assertEqual((result["created"], result["updated"], result["skipped_empty"]), (0, 1, 1))
        self.assertEqual(Risk.objects.count(), 2)  # R47 y R90; la fila vacía R60 no crea nada
        risk.refresh_from_db()
        self.assertEqual(risk.process, "Gestión del éxito y atención del cliente")
        self.assertEqual(list(risk.processes.all()), [self.soporte])
        self.assertEqual(risk.operational_scenario, "Cierre manual")
        self.assertEqual(risk.affected_asset_text, "Web de soporte al cliente")
        self.assertEqual(risk.assessments.count(), 2)  # historial: P3 y luego P4
        self.assertEqual(risk.assessments.first().probability, 4)

    def test_simulacion_muestra_cambios_sin_guardar(self):
        import_workbook(
            workbook("2026.xlsx", HEAD_2026, [row_2026("R47", "Facturación electrónica PSE")]),
            "risks", self.admin, apply=True,
        )
        result = import_workbook(
            workbook("modelo.xlsx", HEAD_MODELO, [row_modelo("R47", "Gestión del éxito y atención del cliente")]),
            "risks", self.admin,
        )
        self.assertEqual(result["updated"], 1)
        self.assertTrue(any("proceso" in change for change in result["changes"]))
        self.assertEqual(Risk.objects.get(code="R47").process, "Facturación electrónica PSE")

    def test_nombre_de_proceso_con_error_de_tipeo_se_vincula_y_se_marca(self):
        import_workbook(
            workbook("modelo.xlsx", HEAD_MODELO, [row_modelo("R52", "Ingenieria y calidad de sofware")]),
            "risks", self.admin, apply=True,
        )
        risk = Risk.objects.get(code="R52")
        self.assertEqual(list(risk.processes.all()), [self.desarrollo])
        self.assertIn("similitud", SourceRow.objects.get(risk=risk).issue)

    def test_ambos_se_vincula_a_ose_y_queda_observado(self):
        import_workbook(
            workbook("2026.xlsx", HEAD_2026, [row_2026("R01", "Ambos")]), "risks", self.admin, apply=True
        )
        risk = Risk.objects.get(code="R01")
        self.assertEqual(list(risk.processes.all()), [self.ose])
        self.assertIn("PSE", SourceRow.objects.get(risk=risk).issue)

    def test_texto_largo_se_recorta_sin_romper_la_importacion(self):
        import_workbook(
            workbook("2026.xlsx", HEAD_2026, [row_2026("R50", "Ambos", threat="x" * 300)]),
            "risks", self.admin, apply=True,
        )
        risk = Risk.objects.get(code="R50")
        self.assertEqual(len(risk.threat), 255)
        self.assertIn("recortado", SourceRow.objects.get(risk=risk).issue)

    def test_tratamiento_importado_toma_el_control_del_anexo_a(self):
        head = HEAD_TRAT + ["Control del Anexo A"]
        with_control = [1, "R47", None, None, "1. Elección de controles", "Implementar MFA"] + [None] * 10 + ["A.8.5 Autenticación segura"]
        without = [2, "R47", None, None, "1. Elección de controles", "Revisión mensual"]
        import_workbook(
            workbook("2026.xlsx", HEAD_2026, [row_2026("R47", "Ambos")], [with_control, without], head),
            "risks", self.admin, apply=True,
        )
        mfa = RiskTreatment.objects.get(action="Implementar MFA")
        self.assertEqual(mfa.control, self.control)
        self.assertEqual(mfa.option, TreatmentOption.CONTROLS)
        pending = RiskTreatment.objects.get(action="Revisión mensual")
        self.assertIsNone(pending.control)
        issue = SourceRow.objects.get(sheet="Tratamiento de riesgos", row_number=6).issue
        self.assertIn("Anexo A", issue)

    # --- Mapa de procesos: resumen de riesgos por proceso ---

    def test_mapa_resume_riesgos_y_tratamientos_sin_control(self):
        self.ose.risks.add(self.risk)
        RiskAssessment.objects.create(
            risk=self.risk, assessed_at=timezone.now(), probability=4, impact=5, inherent_score=20
        )
        RiskTreatment.objects.create(risk=self.risk, option=TreatmentOption.CONTROLS, action="Pendiente de control")
        RiskTreatment.objects.create(
            risk=self.risk, option=TreatmentOption.CONTROLS, action="MFA", control=self.control
        )
        summary = process_payload(self.ose)["risk_summary"]
        self.assertEqual(summary["top_level"], "Muy alto")
        self.assertEqual(summary["levels"]["Muy alto"], 1)
        self.assertEqual(summary["missing_control"], 1)
        self.assertEqual(summary["annex_controls"], [{"code": "8.5", "name": "Autenticación segura"}])
        self.assertEqual(summary["items"][0]["code"], "R90")

    def test_mapa_carga_la_capa_interactiva_y_el_cargador(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("processes:map"))
        self.assertContains(response, "process_map_insights.js")
        self.assertContains(response, "data-sgsi-loader")
        self.assertContains(response, "risk_summary")
