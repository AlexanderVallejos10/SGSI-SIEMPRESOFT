import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.dashboard_live.importer import import_workbook
from apps.dashboard_live.selectors import build_dashboard_context

EXCEL_2026 = Path(settings.BASE_DIR) / "apps" / "dashboard" / "data" / "documentos" / "Dashboard SGSI de SIEMPRESOFT_2026.xlsx"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="sgsi-test-dash-"))
class TableroConElExcel2026(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="dash-admin", business_code="T-DASH", is_superuser=True)
        cls.dataset = import_workbook(path=EXCEL_2026, version_label="2026", actor=cls.admin, original_name=EXCEL_2026.name)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_importa_el_formato_2026(self):
        ds = self.dataset
        self.assertEqual(sorted(ds.sgsi_metrics.values_list("metric_id", flat=True)), [1, 4, 5, 8, 11])  # la 5 repetida, una vez
        self.assertEqual(ds.oesi_metrics.count(), 9)
        self.assertEqual(ds.security_objectives.count(), 9)
        self.assertEqual(ds.strategic_objectives.count(), 8)
        self.assertEqual(ds.stakeholder_requirements.count(), 18)

    def test_calculos_iguales_al_excel(self):
        ctx = build_dashboard_context()
        self.assertEqual(ctx["oee_expected"], 52)  # «Mínimo esperado» del Excel
        self.assertEqual(ctx["oee_obtained"], 45)
        self.assertAlmostEqual(float(ctx["mefi"]["score_sum"]), 4.7857, places=3)
        self.assertAlmostEqual(float(ctx["mefe"]["score_sum"]), 6.1667, places=3)
        self.assertFalse(ctx["mefi"]["weight_warning"])  # 2026 promedia por grupo: no es un error
        self.assertEqual(ctx["oesi_yes"], 5)

    def test_la_pagina_de_inicio_carga_rapido_con_esqueletos(self):
        page = self.client.get(reverse("dashboard_live:home"))
        self.assertContains(page, "Tablero del SGSI")
        self.assertContains(page, reverse("dashboard_live:data"))  # los datos llegan por la API
        self.assertContains(page, "vendor/d3/d3.min.js")           # D3.js incluido en el sistema
        self.assertContains(page, "is-skeleton")                   # esqueletos mientras carga
        self.assertContains(page, "Mapa de calor de riesgos")

    def test_api_del_tablero(self):
        data = self.client.get(reverse("dashboard_live:data")).json()
        self.assertEqual(len(data["sgsi"]), 5)
        self.assertEqual(len(data["oesi"]), 9)
        self.assertEqual(data["summary"]["oee"], [45, 52])
        self.assertEqual(len(data["security"]), 9)
        self.assertEqual(len(data["oee_matrix"]), 8)
        self.assertIn("risks", data["overview"])
        self.assertTrue(data["oesi"][0]["bullet"])
        self.assertTrue(data["version"])

    def test_api_responde_sin_cambios_si_ya_tiene_la_version(self):
        version = self.client.get(reverse("dashboard_live:data")).json()["version"]
        again = self.client.get(reverse("dashboard_live:data"), {"v": version}).json()
        self.assertEqual(again, {"unchanged": True, "version": version})

    def test_la_api_exige_sesion(self):
        self.client.logout()
        self.assertNotEqual(self.client.get(reverse("dashboard_live:data")).status_code, 200)

    def test_volver_a_subir_el_mismo_excel_no_duplica(self):
        again = import_workbook(path=EXCEL_2026, version_label="2026", actor=self.admin, original_name=EXCEL_2026.name)
        self.assertEqual(again.pk, self.dataset.pk)


class DisenoComunEnTodosLosModulos(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="diseno-admin", business_code="T-DIS", is_superuser=True)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_la_capa_de_diseno_y_las_microinteracciones_llegan_a_cada_modulo(self):
        for name, args in (("registers:index", []), ("assets:list", []), ("dashboard_live:home", [])):
            with self.subTest(page=name):
                page = self.client.get(reverse(name, args=args))
                self.assertContains(page, "css/sd_system.css")
                self.assertContains(page, "js/sd_ui.js")
                self.assertContains(page, 'data-accent-value="green"')  # acento en la barra superior
                self.assertContains(page, "data-density-toggle")
