from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.assets.models import Asset


class PantallasUnificadas(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="pant-admin", business_code="T-PANT", is_superuser=True)
        self.client.force_login(self.admin)

    def test_activos_antiguos_llevan_al_modulo_actual(self):
        self.assertRedirects(self.client.get("/gestion/activos/"), reverse("assets:list"), fetch_redirect_response=False)
        asset = Asset.objects.create(code="SS1-LAP-001", asset_type="Laptop", name="Laptop")
        self.assertRedirects(self.client.get(f"/gestion/activos/{asset.pk}/"), reverse("assets:detail", args=[asset.code]),
                             fetch_redirect_response=False)

    def test_riesgos_antiguos_llevan_al_modulo_actual(self):
        self.assertRedirects(self.client.get("/gestion/riesgos/"), reverse("traceability:risks"), fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/gestion/riesgos/nuevo/"), reverse("traceability:risk_new"), fetch_redirect_response=False)

    def test_un_solo_listado_de_colaboradores(self):
        self.assertRedirects(self.client.get("/usuarios/"), reverse("dashboard:entity_list", args=["usuarios"]),
                             fetch_redirect_response=False)

    def test_encabezados_en_espanol(self):
        response = self.client.get(reverse("dashboard:entity_list", args=["incidentes"]))
        self.assertContains(response, "Código")
        self.assertNotContains(response, "Updated At")
        self.assertNotContains(response, "PostgreSQL")

    def test_formulario_de_relaciones_en_espanol(self):
        from apps.processes.forms import ProcessRelationForm

        etiquetas = [str(f.label) for f in ProcessRelationForm().fields.values()]
        self.assertEqual(etiquetas, ["Origen", "Destino", "Tipo de relación", "Etiqueta"])
