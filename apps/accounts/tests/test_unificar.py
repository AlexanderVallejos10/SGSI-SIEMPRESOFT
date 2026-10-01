from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import Notification, UserSession
from apps.accounts.unify import asset_key, duplicate_assets, duplicate_groups, merge
from apps.assets.models import Asset


class UnaPersonaUnCodigo(TestCase):
    def setUp(self):
        User = get_user_model()
        self.real = User.objects.create_user(username="mguevara", business_code="EMP-001", first_name="Milton", last_name="Guevara",
                                             email="mguevara@siempresoft.com", password="Clave-Segura-2026")
        self.dup = User.objects.create(username="milton.guevara.santisteban", business_code="COL-MILTON", first_name="Milton",
                                       last_name="Guevara Santisteban", is_active=False, position="Gerente General")
        self.dup.set_unusable_password()
        self.dup.save()
        self.otro = User.objects.create_user(username="mperez", business_code="EMP-009", first_name="Milton", last_name="Pérez")

    def test_detecta_a_la_misma_persona_y_no_a_otra_con_el_mismo_nombre(self):
        groups = duplicate_groups()
        self.assertEqual(len(groups), 1)
        keep, dups, doubtful = groups[0]
        self.assertEqual(keep, self.real)          # queda la cuenta con contraseña y correo
        self.assertEqual(dups, [self.dup])
        self.assertFalse(doubtful)

    def test_todo_pasa_a_la_cuenta_que_queda(self):
        asset = Asset.objects.create(code="SS1-CPU-001", asset_type="CPU", name="Computadora", custodian=self.dup)
        Notification.objects.create(recipient=self.dup, kind="x", title="Aviso")
        UserSession.objects.create(user=self.dup, session_key="abc")
        merge(self.real, [self.dup])
        asset.refresh_from_db()
        self.real.refresh_from_db()
        self.assertEqual(asset.custodian, self.real)
        self.assertEqual(self.real.notifications.count(), 1)
        self.assertEqual(self.real.connection_sessions.count(), 1)
        self.assertEqual(self.real.last_name, "Guevara Santisteban")  # se completa el apellido
        self.assertEqual(self.real.position, "Gerente General")
        self.assertEqual(self.real.business_code, "EMP-001")          # el código de la cuenta que queda
        self.dup.refresh_from_db()
        self.assertFalse(self.dup.is_active)
        self.assertTrue(self.dup.username.endswith("__dup"))
        self.assertFalse(self.dup.has_usable_password())
        self.assertEqual(duplicate_groups(), [])

    def test_dos_cuentas_con_contrasena_y_correos_distintos_no_se_tocan(self):
        User = get_user_model()
        User.objects.create_user(username="mguevara2", business_code="EMP-777", first_name="Milton", last_name="Guevara",
                                 email="otro@correo.com", password="Otra-Clave-2026")
        self.assertTrue(any(doubtful for _, _, doubtful in duplicate_groups()))

    def test_el_comando_sin_aplicar_no_cambia_nada(self):
        out = StringIO()
        call_command("unificar_personas", stdout=out)
        self.assertIn("Vista previa", out.getvalue())
        self.assertTrue(get_user_model().objects.filter(pk=self.dup.pk).exists())


    def test_la_bitacora_conserva_a_quien_hizo_cada_accion(self):
        from apps.auditlog.models import AuditLog
        from apps.auditlog.services import register_audit_event

        register_audit_event(user=self.dup, module="accounts", action="prueba", entity="User", entity_id=self.dup.pk)
        merge(self.real, [self.dup])
        self.assertTrue(AuditLog.objects.filter(user=self.dup, action="prueba").exists())


class UnActivoUnCodigo(TestCase):
    def test_codigos_equivalentes(self):
        self.assertEqual(asset_key("SS1-CPU-012"), asset_key("ss1 cpu 12"))
        self.assertNotEqual(asset_key("SS1-CPU-012"), asset_key("SS1-CPU-013"))

    def test_activos_con_codigos_equivalentes_se_detectan(self):
        Asset.objects.create(code="SS1-CPU-012", asset_type="CPU", name="Computadora")
        Asset.objects.create(code="SS1-CPU-12", asset_type="CPU", name="Computadora")
        self.assertEqual(len(duplicate_assets()), 1)

    def test_el_activo_duplicado_se_retira_sin_borrarse(self):
        from apps.accounts.unify import merge_assets

        keep = Asset.objects.create(code="SS1-CPU-012", asset_type="CPU", name="Computadora")
        dup = Asset.objects.create(code="SS1-CPU-12", asset_type="CPU", name="Computadora")
        merge_assets(keep, [dup])
        dup.refresh_from_db()
        self.assertEqual(dup.status, "retired")
        self.assertTrue(dup.code.endswith("__dup"))
        self.assertEqual(duplicate_assets(), [])
