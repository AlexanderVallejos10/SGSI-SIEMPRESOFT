from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AvisosDelSistema(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username="av-admin", business_code="T-AV", is_superuser=True))

    def test_la_base_carga_el_componente_unico(self):
        page = self.client.get(reverse("dashboard:entity_list", args=["incidentes"]))
        self.assertContains(page, "js/sgsi_avisos.js")
        self.assertContains(page, "css/avisos.css")

    def test_sin_confirm_del_navegador_en_plantillas(self):
        from pathlib import Path

        from django.conf import settings

        raiz = Path(settings.BASE_DIR) / "templates"
        con_confirm = [p.name for p in raiz.rglob("*.html") if "return confirm(" in p.read_text(encoding="utf-8")]
        self.assertEqual(con_confirm, [])

    def test_ingreso_carga_rive_solo_si_estan_todos_sus_archivos(self):
        from unittest import mock

        self.client.logout()
        with mock.patch("django.contrib.staticfiles.finders.find", return_value=None):
            page = self.client.get(reverse("accounts:login"))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "data-rive-src")
        self.assertContains(page, "js/sgsi_login.js")

    def test_estaticos_con_version_para_no_usar_archivos_viejos(self):
        page = self.client.get(reverse("dashboard:entity_list", args=["incidentes"]))
        self.assertRegex(page.content.decode(), r"js/sgsi_avisos\.js\?v=\d+")
