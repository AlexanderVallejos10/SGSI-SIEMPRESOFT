from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import DashboardDataset, OeeOsiAlignment, SecurityObjective, StrategicObjective


class MatrizConDeshacer(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username="mx-admin", business_code="T-MX", is_superuser=True))
        ds = DashboardDataset.objects.create(code="DS-T", original_name="t.xlsx", file="x.xlsx", checksum_sha256="0" * 64, is_current=True)
        osi = SecurityObjective.objects.create(dataset=ds, code="OESI1", description="", source_column="D")
        oee1 = StrategicObjective.objects.create(dataset=ds, code="OEE1", description="", source_row=5)
        oee2 = StrategicObjective.objects.create(dataset=ds, code="OEE2", description="", source_row=6)
        self.a = OeeOsiAlignment.objects.create(dataset=ds, strategic_objective=oee1, security_objective=osi, relation="P", source_cell="D5")
        self.b = OeeOsiAlignment.objects.create(dataset=ds, strategic_objective=oee2, security_objective=osi, relation="S", source_cell="D6")
        self.url_b = reverse("dashboard_live:toggle_oee_alignment", args=[self.b.pk])

    def test_cambio_informa_todas_las_celdas_afectadas(self):
        data = self.client.post(self.url_b).json()
        self.assertEqual(data["relation"], "P")
        self.assertEqual([(c["relation"], c["previous"]) for c in data["changed"]], [("P", "S"), ("S", "P")])
        self.a.refresh_from_db()
        self.assertEqual(self.a.relation, "S")

    def test_deshacer_restaura_el_estado_anterior(self):
        changed = self.client.post(self.url_b).json()["changed"]
        for c in changed:
            self.assertTrue(self.client.post(c["url"], {"relation": c["previous"]}).json()["ok"])
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual((self.a.relation, self.b.relation), ("P", "S"))

    def test_valor_invalido_no_cambia_nada(self):
        response = self.client.post(self.url_b, {"relation": "X"})
        self.assertEqual(response.status_code, 400)
        self.b.refresh_from_db()
        self.assertEqual(self.b.relation, "S")
