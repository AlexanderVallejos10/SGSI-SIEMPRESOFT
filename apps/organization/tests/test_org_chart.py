from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.organization.models import OrganizationalArea, Position, PositionAssignment


class OrganigramaInteractivo(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username="org-admin", business_code="T-ORG", is_superuser=True)
        cls.karim = User.objects.create_user(username="karim", business_code="USR-MIG-004", first_name="Karim", last_name="Salazar")
        area = OrganizationalArea.objects.create(code="SI", name="Seguridad de la Información")
        cls.gerencia = Position.objects.create(code="PUE-01", title="Gerente General")
        cls.oficial = Position.objects.create(
            code="PUE-02", title="Oficial de seguridad de la información", parent=cls.gerencia, area=area, is_critical=True
        )
        PositionAssignment.objects.create(position=cls.oficial, user=cls.karim, start_date=timezone.localdate())

    def setUp(self):
        self.client.force_login(self.admin)

    def test_el_organigrama_usa_el_lienzo_interactivo(self):
        response = self.client.get(reverse("organization:chart"))
        self.assertContains(response, "data-oc-viewport")
        self.assertContains(response, "js/org_chart.js")
        self.assertContains(response, reverse("organization:position_trace", args=[self.oficial.pk]))
        self.assertNotContains(response, "js/organization.js")

    def test_la_trazabilidad_devuelve_cadena_de_mando_y_personas(self):
        data = self.client.get(reverse("organization:position_trace", args=[self.oficial.pk])).json()
        self.assertEqual(data["title"], "Oficial de seguridad de la información")
        self.assertEqual(data["area"], "Seguridad de la Información")
        self.assertTrue(data["critical"])
        self.assertEqual([c["title"] for c in data["chain"]], ["Gerente General"])
        self.assertEqual(data["people"][0]["name"], "Karim Salazar")
        for key in ("processes", "risks", "treatments", "documents_owned", "documents_access", "reports"):
            self.assertEqual(data[key], [])

    def test_la_trazabilidad_pide_sesion(self):
        self.client.logout()
        response = self.client.get(reverse("organization:position_trace", args=[self.oficial.pk]))
        self.assertEqual(response.status_code, 302)
