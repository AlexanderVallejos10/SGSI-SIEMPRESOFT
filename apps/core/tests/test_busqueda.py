from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.assets.models import Asset
from apps.core.busqueda import buscar, patron


class BusquedaGlobal(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="bq-admin", business_code="T-BQ", is_superuser=True)
        self.karim = User.objects.create_user(username="ksalazar", first_name="Karim", last_name="Salazar", business_code="USR-MIG-004")
        Asset.objects.create(code="SS1-LAP-021", asset_type="Laptop", name="Laptop de Gestión Comercial")
        self.client.force_login(self.admin)

    def grupos(self, q, user=None):
        return {g["clave"]: g for g in buscar(user or self.admin, q)}

    def test_encuentra_colaborador_por_nombre_o_codigo(self):
        self.assertIn("Karim Salazar", [i["texto"] for i in self.grupos("karim")["colaboradores"]["items"]])
        self.assertIn("Karim Salazar", [i["texto"] for i in self.grupos("USR-MIG")["colaboradores"]["items"]])

    def test_ignora_tildes(self):
        self.assertEqual(patron("gestion"), patron("gestión"))
        self.assertTrue(self.grupos("gestion comercial")["activos"]["items"])

    def test_una_letra_sugiere_desde_el_inicio_de_palabra(self):
        textos = [i["texto"] for i in self.grupos("k").get("colaboradores", {}).get("items", [])]
        self.assertIn("Karim Salazar", textos)

    def test_lleva_a_la_pagina_de_cada_resultado(self):
        item = self.grupos("SS1-LAP-021")["activos"]["items"][0]
        self.assertEqual(item["url"], reverse("assets:detail", args=["SS1-LAP-021"]))

    def test_respeta_permisos(self):
        nadie = get_user_model().objects.create_user(username="sin-permisos", business_code="T-NP")
        self.assertNotIn("colaboradores", self.grupos("karim", user=nadie))

    def test_api_y_pagina_de_resultados(self):
        datos = self.client.get(reverse("core:sugerencias"), {"q": "laptop"}).json()
        self.assertIn("activos", [g["clave"] for g in datos["grupos"]])
        pagina = self.client.get(reverse("core:buscar"), {"q": "laptop"})
        self.assertContains(pagina, "SS1-LAP-021")

    def test_barra_presente_en_el_encabezado(self):
        pagina = self.client.get(reverse("dashboard:entity_list", args=["incidentes"]))
        self.assertContains(pagina, "data-busqueda")
        self.assertContains(pagina, "js/sgsi_busqueda.js")
