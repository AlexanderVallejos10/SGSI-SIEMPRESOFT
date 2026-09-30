from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.security import ADMIN_ROLE
from apps.risks.models import Risk, RiskAssessment, RiskTreatment

from .models import ManagementReview, RiskAcceptance
from .services import acceptance_rows, residual_for


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.gerente = User.objects.create_user(username="gg", business_code="T-GG", first_name="Milton", last_name="Guevara", is_superuser=True)
        cls.oficial = User.objects.create_user(username="osi", business_code="T-OSI", first_name="Karim", last_name="Salazar")
        cls.oficial.groups.add(Group.objects.get_or_create(name=ADMIN_ROLE)[0])
        cls.colab = User.objects.create_user(username="colab", business_code="T-CO", first_name="Jose", last_name="Torres")


class RevisionPorLaDireccion(Base):
    def test_se_prepara_con_datos_del_sistema_y_la_aprueba_solo_el_gerente(self):
        self.client.force_login(self.oficial)
        self.client.post(reverse("governance:review_create"), {"title": "Revisión 2026", "review_date": "2026-10-15"})
        review = ManagementReview.objects.get()
        self.assertEqual(review.code, "RD-2026-01")
        for key in ("d1_corrective", "d3_audits", "f_risks", "incidents"):
            self.assertIn(key, review.inputs)
        url = reverse("governance:review_detail", args=[review.pk])
        self.client.post(url, {"action": "decision", "description": "Aprobar el presupuesto anual del SGSI", "kind": "recursos",
                               "responsible": str(self.gerente.pk), "due_date": "2026-12-15"})
        self.assertEqual(review.decisions.count(), 1)
        self.assertEqual(self.client.post(url, {"action": "approve"}).status_code, 403)  # el oficial no aprueba
        self.client.force_login(self.gerente)
        self.client.post(url, {"action": "approve"})
        review.refresh_from_db()
        self.assertEqual(review.status, "approved")
        self.assertTrue(self.gerente.notifications.filter(kind="revision_direccion").exists())

    def test_una_revision_aprobada_ya_no_se_edita(self):
        review = ManagementReview.objects.create(code="RD-2026-09", title="Cerrada", review_date=timezone.localdate(), status="approved")
        self.client.force_login(self.oficial)
        self.assertEqual(self.client.post(reverse("governance:review_detail", args=[review.pk]), {"action": "texts", "conclusions": "x"}).status_code, 403)

    def test_un_colaborador_la_puede_leer_pero_no_crear(self):
        self.client.force_login(self.colab)
        self.assertEqual(self.client.get(reverse("governance:review_list")).status_code, 200)
        self.assertEqual(self.client.post(reverse("governance:review_create"), {}).status_code, 403)


class AceptacionDelRiesgo(Base):
    def setUp(self):
        self.risk = Risk.objects.create(code="R50", process="Validación OSE", scenario="Prueba", event="Rechazo de comprobantes", owner=self.colab)
        RiskAssessment.objects.create(risk=self.risk, assessed_at=timezone.now(), probability=3, impact=4, inherent_score=12)

    def test_residual_con_la_tabla_de_la_metodologia(self):
        RiskTreatment.objects.create(risk=self.risk, action="Pruebas de regresión", residual_probability=2, residual_impact=2)
        self.assertEqual(residual_for(self.risk)[2], "Bajo")

    def test_el_propietario_acepta_un_residual_bajo(self):
        RiskTreatment.objects.create(risk=self.risk, action="Pruebas de regresión", residual_probability=2, residual_impact=2)
        self.client.force_login(self.colab)
        self.client.post(reverse("governance:acceptance"), {"risk": self.risk.pk, "decision": "accepted", "justification": "Queda cubierto con las pruebas."})
        self.assertTrue(RiskAcceptance.objects.filter(risk=self.risk, decision="accepted", residual_level="Bajo").exists())

    def test_un_residual_alto_solo_lo_acepta_el_gerente(self):
        self.client.force_login(self.colab)  # sin tratamiento: se decide sobre el inherente (Alto)
        self.client.post(reverse("governance:acceptance"), {"risk": self.risk.pk, "decision": "accepted", "justification": "Intento del propietario."})
        self.assertFalse(RiskAcceptance.objects.exists())
        self.client.force_login(self.gerente)
        self.client.post(reverse("governance:acceptance"), {"risk": self.risk.pk, "decision": "accepted", "justification": "Se asume hasta el cambio normativo."})
        self.assertTrue(RiskAcceptance.objects.filter(residual_level="", inherent_level="Alto").exists())

    def test_si_el_nivel_cambia_la_aceptacion_vence(self):
        RiskAcceptance.objects.create(risk=self.risk, inherent_level="Medio", residual_level="", justification="Antigua", decided_by=self.gerente)
        row = acceptance_rows(Risk.objects.filter(pk=self.risk.pk))[0]
        self.assertIsNone(row["acceptance"])
        self.assertTrue(row["outdated"])


class RevisionDeAccesos(Base):
    def test_mantener_programa_la_siguiente_y_revocar_la_cierra(self):
        from apps.accounts.models import AccessReview, CorporateSystem, SystemAccess

        erp = CorporateSystem.objects.create(business_code="SYS-ERP", name="ERP SiempreSoft")
        keep = SystemAccess.objects.create(business_code="ACC-1", user=self.colab, system=erp, status="active")
        drop = SystemAccess.objects.create(business_code="ACC-2", user=self.colab, system=erp, status="active")
        self.client.force_login(self.oficial)
        self.client.post(reverse("governance:access_review"), {"access": keep.pk, "decision": "keep"})
        self.client.post(reverse("governance:access_review"), {"access": drop.pk, "decision": "revoke", "comments": "Cambió de área"})
        keep.refresh_from_db()
        drop.refresh_from_db()
        self.assertEqual((keep.next_review_at - timezone.localdate()).days, 90)
        self.assertEqual(drop.status, "revoked")
        self.assertEqual(AccessReview.objects.count(), 2)

    def test_solo_administradores(self):
        self.client.force_login(self.colab)
        self.assertEqual(self.client.get(reverse("governance:access_review")).status_code, 403)


class DeclaracionDeAplicabilidad(Base):
    def test_se_puede_consultar(self):
        self.client.force_login(self.colab)
        self.assertContains(self.client.get(reverse("governance:soa")), "Declaración de Aplicabilidad")
