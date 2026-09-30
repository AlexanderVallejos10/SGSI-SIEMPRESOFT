import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .layout import free_slot
from .models import ProcessCategory, ProcessNode, ProcessRelation


class MapaDinamico(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="admin-map", business_code="T-MAP", is_superuser=True
        )
        self.client.force_login(self.admin)
        self.strategic = ProcessCategory.objects.create(code="C-E", name="Estratégicos", kind="strategic", sort_order=10)
        self.operational = ProcessCategory.objects.create(code="C-O", name="Operativos", kind="operational", sort_order=20)
        self.support = ProcessCategory.objects.create(code="C-A", name="Apoyo", kind="support", sort_order=30)
        # La migración 0005 ya crea las categorías de partes interesadas y sus nodos.
        self.party = ProcessCategory.objects.get(kind="input")

    def node(self, code, category, x=40, y=40):
        return ProcessNode.objects.create(code=code, name=code, category=category, x=x, y=y)

    def test_lugar_libre_no_se_superpone(self):
        self.node("A", self.support, 40, 40)
        self.node("B", self.support, 255, 40)
        self.assertEqual(free_slot(self.support), (470, 40))

    def test_arrastrar_cambia_la_categoria_y_conserva_relaciones(self):
        rrhh = self.node("RRHH", self.support)
        ventas = self.node("VENTAS", self.operational)
        ProcessRelation.objects.create(source=rrhh, target=ventas)
        response = self.client.post(
            reverse("processes:save_layout"),
            json.dumps({"moves": [{"id": str(rrhh.pk), "x": 300, "y": 120, "category": "operational"}]}),
            content_type="application/json",
        )
        self.assertTrue(response.json()["ok"])
        rrhh.refresh_from_db()
        self.assertEqual((rrhh.category.kind, rrhh.x, rrhh.y), ("operational", 300, 120))
        self.assertEqual(rrhh.outgoing_relations.count(), 1)

    def test_una_parte_interesada_no_se_convierte_en_proceso_al_arrastrar(self):
        cliente = self.node("CLIENTE", self.party, 0, 0)
        self.client.post(
            reverse("processes:save_layout"),
            json.dumps({"moves": [{"id": str(cliente.pk), "x": 100, "y": 100, "category": "operational"}]}),
            content_type="application/json",
        )
        cliente.refresh_from_db()
        self.assertEqual(cliente.category.kind, "input")

    def test_editar_la_categoria_ubica_el_proceso_en_su_nueva_franja(self):
        self.node("OCUPADO", self.strategic, 40, 40)
        mkt = self.node("MKT", self.support, 40, 40)
        data = {"code": "MKT", "name": "Marketing", "category": self.strategic.pk, "is_active": "on", "is_in_scope": "on"}
        self.client.post(reverse("processes:process_edit", args=[mkt.pk]), data)
        mkt.refresh_from_db()
        self.assertEqual(mkt.category, self.strategic)
        self.assertEqual((mkt.x, mkt.y), (255, 40))

    def test_mapa_v015_crea_partes_interesadas_y_sus_flujos(self):
        call_command("configure_sgsi_structure", "--apply", "--map", verbosity=0)
        cliente = ProcessNode.objects.get(code="PARTE-CLIENTE-PSE")
        sunat = ProcessNode.objects.get(code="PARTE-CLIENTE-SUNAT")
        self.assertEqual((cliente.category.kind, sunat.category.kind), ("input", "output"))
        self.assertTrue(cliente.outgoing_relations.filter(target__code="PROC-OSE", is_active=True).exists())
        self.assertEqual(sunat.incoming_relations.filter(is_active=True).count(), 3)
        page = self.client.get(reverse("processes:map"))
        self.assertContains(page, "process-party")
        self.assertContains(page, "processes_map.js")

    def test_la_migracion_deja_cliente_pse_y_sunat_en_el_mapa(self):
        self.assertTrue(ProcessNode.objects.filter(code="PARTE-CLIENTE-PSE", category__kind="input").exists())
        self.assertTrue(ProcessNode.objects.filter(code="PARTE-CLIENTE-SUNAT", category__kind="output").exists())

    def test_crear_relacion_desde_una_parte_interesada_y_reactivarla(self):
        cliente = ProcessNode.objects.get(code="PARTE-CLIENTE-PSE")
        infra = self.node("INFRA", self.support)
        url = reverse("processes:relation_create")
        data = {"source": cliente.pk, "target": infra.pk, "relation_type": "flow", "label": ""}
        first = self.client.post(url, data, HTTP_ACCEPT="application/json").json()
        self.assertTrue(first["ok"])
        relation = ProcessRelation.objects.get(pk=first["relation"]["id"])
        self.client.post(reverse("processes:relation_archive", args=[relation.pk]), HTTP_ACCEPT="application/json")
        relation.refresh_from_db()
        self.assertFalse(relation.is_active)
        again = self.client.post(url, data, HTTP_ACCEPT="application/json").json()
        self.assertEqual(again["relation"]["id"], str(relation.pk))
        relation.refresh_from_db()
        self.assertTrue(relation.is_active)

    def test_no_permite_relacionar_un_proceso_consigo_mismo(self):
        infra = self.node("INFRA", self.support)
        response = self.client.post(
            reverse("processes:relation_create"),
            {"source": infra.pk, "target": infra.pk, "relation_type": "flow"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ProcessRelation.objects.filter(source=infra).exists())
