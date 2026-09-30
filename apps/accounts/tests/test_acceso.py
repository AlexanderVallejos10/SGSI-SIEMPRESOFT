import time
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import LoginAttempt, Notification, PasswordChangeRequest, UserSession
from apps.accounts.security import ADMIN_ROLE, issue_credentials, sync_admin_role


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        Group.objects.get_or_create(name=ADMIN_ROLE)
        Group.objects.get_or_create(name="Usuario / Colaborador")
        sync_admin_role()
        cls.gerente = User.objects.create_user(username="mguevara", business_code="COL-MG", first_name="Milton", last_name="Guevara",
                                               email="mguevara@siempresoft.com", password="Gerente-Seguro-2026")
        cls.gerente.groups.add(Group.objects.get(name=ADMIN_ROLE))
        cls.colab = User.objects.create_user(username="jtorres", business_code="COL-JT", first_name="Jose", last_name="Torres",
                                             email="jtorres@siempresoft.com", password="Colaborador-2026x")

    def login(self, username, password):
        return self.client.post(reverse("accounts:login"), {"username": username, "password": password})


class IngresoYBloqueo(Base):
    def test_sin_sesion_todo_lleva_al_ingreso(self):
        page = self.client.get(reverse("dashboard_live:home"))
        self.assertEqual(page.status_code, 302)
        self.assertIn(reverse("accounts:login"), page["Location"])

    def test_ingreso_correcto_registra_la_sesion(self):
        self.login("jtorres", "Colaborador-2026x")
        self.assertTrue(UserSession.objects.filter(user=self.colab, ended_at__isnull=True).exists())
        self.client.post(reverse("accounts:logout"))
        s = UserSession.objects.get(user=self.colab)
        self.assertEqual(s.ended_reason, "logout")

    def test_cinco_intentos_fallidos_bloquean_aunque_luego_acierte(self):
        for _ in range(5):
            self.login("jtorres", "mala")
        self.assertEqual(LoginAttempt.objects.filter(username="jtorres", success=False).count(), 5)
        page = self.login("jtorres", "Colaborador-2026x")
        self.assertContains(page, "Demasiados intentos fallidos")
        self.assertFalse(UserSession.objects.filter(user=self.colab).exists())


class Contrasenas(Base):
    def test_credenciales_temporales_obligan_a_cambiar_al_ingresar(self):
        username, password = issue_credentials(self.colab, self.gerente)
        self.assertTrue(get_user_model().objects.get(pk=self.colab.pk).must_change_password)
        response = self.login(username, password)
        self.assertRedirects(response, reverse("accounts:password_change"), fetch_redirect_response=False)
        # mientras no la cambie, cualquier página lo devuelve al cambio de contraseña
        self.assertRedirects(self.client.get(reverse("registers:index")), reverse("accounts:password_change"), fetch_redirect_response=False)
        self.client.post(reverse("accounts:password_change"), {"new_password1": "MiClave-Nueva-2026", "new_password2": "MiClave-Nueva-2026"})
        user = get_user_model().objects.get(pk=self.colab.pk)
        self.assertFalse(user.must_change_password)
        self.assertEqual(user.password_changes, 1)
        self.assertEqual(self.client.get(reverse("registers:index")).status_code, 200)

    def test_colaborador_cambia_una_sola_vez_y_despues_solicita(self):
        self.client.force_login(self.colab)
        self.client.post(reverse("accounts:password_change"), {"current_password": "Colaborador-2026x",
                                                                "new_password1": "Otra-Clave-2026", "new_password2": "Otra-Clave-2026"})
        page = self.client.get(reverse("accounts:password_change"))
        self.assertContains(page, "Solicitar cambio de contraseña")
        self.client.post(reverse("accounts:password_request"), {"reason": "La compartí por error con un proveedor."})
        self.assertTrue(PasswordChangeRequest.objects.filter(user=self.colab, status="pending").exists())
        self.assertTrue(Notification.objects.filter(recipient=self.gerente, kind="solicitud_contrasena").exists())

    def test_administrador_puede_cambiar_su_contrasena_varias_veces(self):
        self.client.force_login(self.gerente)
        for n, (old, new) in enumerate([("Gerente-Seguro-2026", "Gerente-Nueva-2026a"), ("Gerente-Nueva-2026a", "Gerente-Otra-2026b")], start=1):
            self.client.post(reverse("accounts:password_change"), {"current_password": old, "new_password1": new, "new_password2": new})
            self.assertEqual(get_user_model().objects.get(pk=self.gerente.pk).password_changes, n)

    def test_aprobar_la_solicitud_genera_una_contrasena_temporal(self):
        req = PasswordChangeRequest.objects.create(user=self.colab, reason="Necesito cambiarla otra vez.")
        self.client.force_login(self.gerente)
        page = self.client.post(reverse("accounts:password_request_resolve", args=[req.pk]), {"decision": "approve"}, follow=True)
        self.assertContains(page, "Credenciales generadas")
        req.refresh_from_db()
        self.assertEqual(req.status, "approved")
        self.assertTrue(get_user_model().objects.get(pk=self.colab.pk).must_change_password)


class Permisos(Base):
    def test_colaborador_no_entra_a_accesos(self):
        self.client.force_login(self.colab)
        self.assertEqual(self.client.get(reverse("accounts:access_list")).status_code, 403)

    def test_casillas_asignan_rol_y_permisos_por_modulo(self):
        self.client.force_login(self.gerente)
        self.client.post(reverse("accounts:access_user", args=[self.colab.pk]),
                         {"action": "save", "roles": ["Usuario / Colaborador"], "active": "1", "mod_riesgos": "edit", "mod_activos": "view"})
        user = get_user_model().objects.get(pk=self.colab.pk)
        self.assertTrue(user.has_perm("risks.change_risk"))
        self.assertTrue(user.has_perm("assets.view_asset"))
        self.assertFalse(user.has_perm("assets.change_asset"))
        self.assertTrue(Notification.objects.filter(recipient=user, kind="permisos").exists())

    def test_nadie_se_quita_su_propio_rol_de_administrador(self):
        self.client.force_login(self.gerente)
        self.client.post(reverse("accounts:access_user", args=[self.gerente.pk]), {"action": "save", "roles": [], "active": "1"})
        self.assertTrue(self.gerente.groups.filter(name=ADMIN_ROLE).exists())

    def test_generar_credenciales_en_bloque(self):
        self.client.force_login(self.gerente)
        page = self.client.post(reverse("accounts:access_bulk"), {"action": "credentials", "users": [str(self.colab.pk)]}, follow=True)
        self.assertContains(page, "jtorres")
        self.assertTrue(get_user_model().objects.get(pk=self.colab.pk).must_change_password)


class PresenciaYSesiones(Base):
    def test_pulso_devuelve_conectados_y_notificaciones(self):
        self.client.force_login(self.colab)
        Notification.objects.create(recipient=self.colab, kind="prueba", title="Aviso de prueba")
        data = self.client.get(reverse("accounts:pulse")).json()
        self.assertTrue(any(p["me"] for p in data["online"]))
        self.assertEqual(data["unread"], 1)
        self.assertEqual(data["notifications"][0]["title"], "Aviso de prueba")

    def test_inactividad_cierra_la_sesion(self):
        self.login("jtorres", "Colaborador-2026x")
        session = self.client.session
        session["activity_ts"] = time.time() - 60 * 60
        session.save()
        response = self.client.get(reverse("registers:index"))
        self.assertIn(reverse("accounts:login"), response["Location"])
        self.assertEqual(UserSession.objects.get(user=self.colab).ended_reason, "inactividad")


class VersionDelManual(Base):
    def test_solo_administradores_cambian_la_version(self):
        from apps.documents.models import ManualReference

        self.client.force_login(self.colab)
        self.assertEqual(self.client.post(reverse("dashboard:manual_reference_update"), {"version": "0.8", "change_note": "x"}).status_code, 403)
        self.client.force_login(self.gerente)
        self.client.post(reverse("dashboard:manual_reference_update"),
                         {"version": "0.8", "status": "Vigente", "change_note": "Aprobado en la revisión por la Dirección.", "next": "/"})
        current = ManualReference.objects.get(is_current=True)
        self.assertEqual((current.version, current.status), ("0.8", "Vigente"))
        self.assertEqual(ManualReference.objects.count(), 2)  # la v0.7 de partida queda en el historial


class ConfiguracionInicial(TestCase):
    def test_configurar_accesos_detecta_administradores_y_genera_credenciales(self):
        User = get_user_model()
        ks = User.objects.create(username="ksalazar", business_code="COL-KS", email="ksalazar@siempresoft.com", is_active=False)
        ks.set_unusable_password()
        ks.save()
        out = StringIO()
        call_command("configurar_accesos", stdout=out)
        ks.refresh_from_db()
        self.assertTrue(ks.groups.filter(name=ADMIN_ROLE).exists())
        self.assertTrue(ks.is_active and ks.must_change_password)
        self.assertIn("ksalazar", out.getvalue())


import base64
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
MEDIA_TMP = tempfile.mkdtemp(prefix="sgsi-media-")


@override_settings(MEDIA_ROOT=MEDIA_TMP)
class FotosDePerfil(Base):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TMP, ignore_errors=True)

    def test_sube_su_foto_y_aparece_en_los_conectados(self):
        self.client.force_login(self.colab)
        self.client.post(reverse("accounts:profile"), {"photo": SimpleUploadedFile("yo.png", PNG_1X1, content_type="image/png")})
        user = get_user_model().objects.get(pk=self.colab.pk)
        self.assertTrue(user.photo.name.startswith("avatares/"))
        self.assertNotIn("torres", user.photo.name.lower())  # el archivo no lleva el nombre de la persona
        me = next(p for p in self.client.get(reverse("accounts:pulse")).json()["online"] if p["me"])
        self.assertTrue(me["photo"])

    def test_un_archivo_que_no_es_imagen_se_rechaza(self):
        self.client.force_login(self.colab)
        page = self.client.post(reverse("accounts:profile"), {"photo": SimpleUploadedFile("foto.jpg", b"MZ no soy una imagen", content_type="image/jpeg")}, follow=True)
        self.assertContains(page, "Use una foto JPG, PNG o WebP")
        self.assertFalse(get_user_model().objects.get(pk=self.colab.pk).photo)

    def test_quitar_la_foto_deja_las_iniciales(self):
        self.client.force_login(self.colab)
        self.client.post(reverse("accounts:profile"), {"photo": SimpleUploadedFile("yo.png", PNG_1X1, content_type="image/png")})
        self.client.post(reverse("accounts:profile"), {"action": "remove_photo"})
        page = self.client.get(reverse("accounts:profile"))
        self.assertContains(page, ">JT<")

    def test_el_administrador_cambia_la_foto_de_otra_persona_y_se_le_avisa(self):
        self.client.force_login(self.gerente)
        self.client.post(reverse("accounts:access_user", args=[self.colab.pk]),
                         {"action": "photo", "photo": SimpleUploadedFile("jt.png", PNG_1X1, content_type="image/png")})
        self.assertTrue(get_user_model().objects.get(pk=self.colab.pk).photo)
        self.assertTrue(Notification.objects.filter(recipient=self.colab, kind="foto").exists())
