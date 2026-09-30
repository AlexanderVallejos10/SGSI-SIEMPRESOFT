import datetime
import io
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.controls.models import Control, ControlFramework
from apps.controls.models_iso import ISOClause
from apps.documents.models import Document, DocumentVersion, SGSISection
from apps.risks.models import Risk, RiskTreatment, TreatmentOption

from .file_serving import serve_artifact
from .manual_sgsi import manual_for
from .selectors import get_annex_context


class _Stored:
    def __init__(self, data):
        self.data = data
        self.size = len(data)

    def open(self, mode="rb"):
        return io.BytesIO(self.data)


def fake_artifact(data=b"%PDF-1.4 " + b"x" * 1000):
    return SimpleNamespace(
        pk="abc", file=_Stored(data), original_name="manual.pdf",
        updated_at=datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc),
    )


class EntregaDePdf(TestCase):
    def test_devuelve_solo_el_rango_pedido(self):
        artifact = fake_artifact()
        request = RequestFactory().get("/", HTTP_RANGE="bytes=0-99")
        response = serve_artifact(request, artifact, "application/pdf")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], f"bytes 0-99/{artifact.file.size}")
        self.assertEqual(len(b"".join(response.streaming_content)), 100)

    def test_no_reenvia_un_pdf_que_el_navegador_ya_tiene(self):
        artifact = fake_artifact()
        first = serve_artifact(RequestFactory().get("/"), artifact, "application/pdf")
        again = serve_artifact(RequestFactory().get("/", HTTP_IF_NONE_MATCH=first["ETag"]), artifact, "application/pdf")
        self.assertEqual(again.status_code, 304)
        self.assertEqual(first["Accept-Ranges"], "bytes")
        self.assertIn("inline", first["Content-Disposition"])


class ClausulasYManual(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="u-cl", business_code="T-CL", is_superuser=True)
        self.client.force_login(self.user)
        self.iso = ControlFramework.objects.create(code="ISO27001-2022", name="ISO/IEC 27001", version="2022")

    def test_el_manual_enlaza_la_clausula_con_su_modulo(self):
        info = manual_for("4.3")
        self.assertIn("Mapa de procesos SIEMPRESOFT", info["documents"])
        self.assertEqual(info["modules"][0]["url"], reverse("processes:map"))

    def test_la_pagina_de_clausula_muestra_la_guia_del_manual(self):
        ISOClause.objects.create(framework=self.iso, code="4", title="Contexto de la organización")
        ISOClause.objects.create(framework=self.iso, code="4.3", title="Alcance del SGSI")
        response = self.client.get(reverse("dashboard:clause_detail", args=["4"]))
        self.assertContains(response, "Documentos que exige el Manual")
        self.assertContains(response, "Documento sobre el alcance del SGSI")
        self.assertContains(response, reverse("processes:map"))
        self.assertContains(response, "clause_page.js")

    def test_declaracion_de_aplicabilidad_detecta_controles_en_contradiccion(self):
        control = Control.objects.create(framework=self.iso, code="8.5", name="Autenticación segura", applicability="not_applicable")
        risk = Risk.objects.create(code="R01", process="OSE", scenario="Acceso indebido")
        RiskTreatment.objects.create(risk=risk, option=TreatmentOption.CONTROLS, action="MFA", control=control)
        annex = get_annex_context()
        self.assertEqual([c.code for c in annex["soa_conflicts"]], ["8.5"])
        page = self.client.get(reverse("dashboard:control_detail", args=[control.pk]))
        self.assertContains(page, "Riesgos que justifican este control")
        self.assertContains(page, "R01")

    def test_la_matriz_muestra_los_documentos_asignados_a_la_seccion(self):
        # 4.1, 4.2 y 4.3 tienen páginas propias (contexto, partes interesadas y mapa de procesos).
        ISOClause.objects.create(framework=self.iso, code="4.4", title="Sistema de gestión de seguridad de la información")
        section = SGSISection.objects.create(code="4.4", title="Sistema de gestión de seguridad de la información")
        document = Document.objects.create(code="DOC-PI", title="Partes Interesadas")
        document.sgsi_sections.add(section)
        response = self.client.get(reverse("dashboard:clause_detail", args=["4.4"]))
        self.assertContains(response, "Partes Interesadas")

    def test_el_numeral_pide_solo_los_documentos_del_manual(self):
        ISOClause.objects.create(framework=self.iso, code="6.1", title="Acciones para tratar los riesgos y las oportunidades")
        response = self.client.get(reverse("dashboard:clause_detail", args=["6.1"]))
        self.assertContains(response, "Metodología para la evaluación y tratamiento de Riesgos")
        self.assertContains(response, "No está cargado en el sistema")
        self.assertNotContains(response, "Misión y Visión")  # pertenece a 4.1, no a 6.1

    def test_registrar_un_documento_del_manual_lo_asigna_al_numeral(self):
        SGSISection.objects.create(code="4.3", title="Alcance del SGSI")
        response = self.client.post(
            reverse("dashboard:manual_register"), {"numeral": "4.3", "name": "Documento sobre el alcance del SGSI"}
        )
        document = Document.objects.get(title="Documento sobre el alcance del SGSI")
        self.assertEqual(document.code, "MAN-4-3-01")
        self.assertEqual(list(document.sgsi_sections.values_list("code", flat=True)), ["4.3"])
        self.assertRedirects(response, reverse("dashboard:document_detail", args=[document.pk]) + "#nueva-version", fetch_redirect_response=False)

    def test_el_numeral_muestra_cada_documento_abierto_como_en_4_1(self):
        ISOClause.objects.create(framework=self.iso, code="6.1", title="Acciones para tratar los riesgos y las oportunidades")
        response = self.client.get(reverse("dashboard:clause_detail", args=["6.1"]))
        self.assertContains(response, 'class="mdoc is-missing"')
        self.assertContains(response, "Ver contenido")
        self.assertContains(response, "Subir el documento")

    def test_la_lista_del_manual_se_edita_sin_tocar_el_codigo(self):
        from apps.documents.models import ManualDocumentRequirement

        ISOClause.objects.create(framework=self.iso, code="6.1", title="Acciones para tratar los riesgos y las oportunidades")
        ManualDocumentRequirement.objects.filter(numeral="6.1", name__startswith="Metodología").update(is_active=False)
        ManualDocumentRequirement.objects.create(numeral="6.1", name="Inventario de servicios en la nube", manual_version="0.8")
        response = self.client.get(reverse("dashboard:clause_detail", args=["6.1"]))
        self.assertContains(response, "Inventario de servicios en la nube")
        self.assertNotContains(response, "Metodología para la evaluación y tratamiento de Riesgos")

    def test_las_versiones_se_leen_del_nombre_y_gana_la_mas_alta(self):
        from apps.dashboard.selectors import _normalize, version_label, version_rank

        self.assertGreater(version_rank("Metodologia_V0.10.pdf"), version_rank("Metodologia_V0.9"))
        self.assertEqual(version_label("ORGANIGRAMA V. 21.pdf"), "21")
        self.assertEqual(
            _normalize("Lista_de_requisitos_legales_V0.13 - BORRADOR (1)"),
            _normalize("Lista de requisitos legales V0.14"),
        )


@override_settings(MEDIA_ROOT="/tmp/sgsi-test-media")
class VersionesDeDocumento(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="u-doc", business_code="T-DOC", is_superuser=True)
        self.client.force_login(self.user)
        self.document = Document.objects.create(code="DOC-LR", title="Lista de requisitos legales")
        DocumentVersion.objects.create(
            document=self.document, version="0.12", file=SimpleUploadedFile("v12.pdf", b"%PDF-1.4 v12"), status="active"
        )

    def test_subir_una_version_vigente_deja_la_anterior_en_el_historial(self):
        url = reverse("dashboard:document_detail", args=[self.document.pk])
        response = self.client.post(url, {
            "file": SimpleUploadedFile("v13.pdf", b"%PDF-1.4 v13"),
            "version": "0.13",
            "reason": "Se agregan requisitos de datos personales",
            "status": "active",
        })
        self.assertEqual(response.status_code, 302)
        versions = {v.version: v.status for v in self.document.versions.all()}
        self.assertEqual(versions, {"0.12": "obsolete", "0.13": "active"})
        page = self.client.get(url)
        self.assertContains(page, "Historial de versiones")
        self.assertContains(page, "Se agregan requisitos de datos personales")

    def test_no_permite_repetir_un_numero_de_version(self):
        url = reverse("dashboard:document_detail", args=[self.document.pk])
        response = self.client.post(url, {
            "file": SimpleUploadedFile("otra.pdf", b"%PDF-1.4"), "version": "0.12", "reason": "x", "status": "draft",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.document.versions.count(), 1)

    def test_el_archivo_de_una_version_se_sirve_por_rangos(self):
        version = self.document.versions.get()
        response = self.client.get(reverse("dashboard:version_file", args=[version.pk]), HTTP_RANGE="bytes=0-3")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF")


class TemaYVisor(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="u-tema", business_code="T-TEMA", is_superuser=True)
        self.client.force_login(self.user)

    def test_la_base_trae_selector_de_tema_visor_y_sin_avalue(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "data-theme-switch")
        self.assertContains(response, "css/theme.css")
        self.assertContains(response, "js/pdf_viewer.js")
        self.assertContains(response, "vendor/pdfjs/pdf.min.js")
        self.assertNotContains(response, "aValue")
