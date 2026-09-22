from django.contrib.auth.models import Group
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from apps.accounts.models import User
from apps.auditlog.context import (
    AuditRequestContext,
    reset_audit_context,
    set_audit_context,
)
from apps.auditlog.models import AuditLog


class SecurityAuditTests(TestCase):
    """
    Pruebas de auditoría relacionadas con:

    - Asignación de roles.
    - Retiro de roles.
    - Login exitoso.
    - Logout.
    - Login fallido.
    - Protección de contraseñas.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="security.audit",
            business_code="USR-SEC-001",
            email="security.audit@siempresoft.local",
            password="Temporal123!",
        )

        self.factory = RequestFactory()

    def make_request(self):
        """
        Crea una petición HTTP simulada con sesión,
        sin utilizar la base productiva.
        """

        request = self.factory.get(
            "/",
            REMOTE_ADDR="127.0.0.1",
        )

        middleware = SessionMiddleware(
            lambda request: None
        )

        middleware.process_request(request)

        request.session.save()

        return request

    def test_role_assignment_and_removal_are_audited(self):
        """
        Comprueba:

        Usuario + Rol     -> RELATION_ADD
        Usuario - Rol     -> RELATION_REMOVE
        """

        group = Group.objects.create(
            name="Rol de prueba",
        )

        token = set_audit_context(
            AuditRequestContext(
                user=self.user,
                ip_address="127.0.0.1",
                session_key="m2m-session",
            )
        )

        try:
            # ==============================================
            # ASIGNAR ROL
            # ==============================================

            self.user.groups.add(group)

            add_log = AuditLog.objects.get(
                action="RELATION_ADD",
                entity="accounts.user",
                entity_id="USR-SEC-001",
            )

            self.assertEqual(
                add_log.user_id,
                self.user.id,
            )

            self.assertEqual(
                add_log.ip_address,
                "127.0.0.1",
            )

            self.assertEqual(
                add_log.session_key,
                "m2m-session",
            )

            self.assertEqual(
                add_log.after["field"],
                "groups",
            )

            self.assertEqual(
                add_log.after["related_model"],
                "auth.group",
            )

            self.assertIn(
                str(group.pk),
                add_log.after["related_ids"],
            )

            # ==============================================
            # RETIRAR ROL
            # ==============================================

            self.user.groups.remove(group)

            remove_log = AuditLog.objects.get(
                action="RELATION_REMOVE",
                entity="accounts.user",
                entity_id="USR-SEC-001",
            )

            self.assertEqual(
                remove_log.before["field"],
                "groups",
            )

            self.assertEqual(
                remove_log.before["related_model"],
                "auth.group",
            )

            self.assertIn(
                str(group.pk),
                remove_log.before["related_ids"],
            )

            self.assertEqual(
                remove_log.after["related_ids"],
                [],
            )

        finally:
            reset_audit_context(token)

    def test_login_logout_and_failed_login_are_audited(self):
        """
        Comprueba:

        LOGIN
        LOGOUT
        LOGIN_FAILED

        También confirma que una contraseña incorrecta
        jamás se almacene en AuditLog.
        """

        request = self.make_request()

        # ==============================================
        # LOGIN EXITOSO
        # ==============================================

        user_logged_in.send(
            sender=User,
            request=request,
            user=self.user,
        )

        login_log = AuditLog.objects.get(
            action="LOGIN",
            entity="accounts.user",
            entity_id="USR-SEC-001",
        )

        self.assertEqual(
            login_log.user_id,
            self.user.id,
        )

        self.assertEqual(
            login_log.ip_address,
            "127.0.0.1",
        )

        self.assertEqual(
            login_log.result,
            "success",
        )

        self.assertEqual(
            login_log.after["event"],
            "login",
        )

        # ==============================================
        # LOGOUT
        # ==============================================

        user_logged_out.send(
            sender=User,
            request=request,
            user=self.user,
        )

        logout_log = AuditLog.objects.get(
            action="LOGOUT",
            entity="accounts.user",
            entity_id="USR-SEC-001",
        )

        self.assertEqual(
            logout_log.user_id,
            self.user.id,
        )

        self.assertEqual(
            logout_log.result,
            "success",
        )

        self.assertEqual(
            logout_log.after["event"],
            "logout",
        )

        # ==============================================
        # LOGIN FALLIDO
        # ==============================================

        fake_password = "NUNCA-GUARDAR-ESTO"

        user_login_failed.send(
            sender=User,
            credentials={
                "username": "usuario.inexistente",
                "password": fake_password,
            },
            request=request,
        )

        failed_log = AuditLog.objects.get(
            action="LOGIN_FAILED",
            entity="accounts.user",
            entity_id="usuario.inexistente",
        )

        self.assertIsNone(
            failed_log.user_id,
        )

        self.assertEqual(
            failed_log.result,
            "failed",
        )

        self.assertEqual(
            failed_log.ip_address,
            "127.0.0.1",
        )

        self.assertEqual(
            failed_log.after["identifier"],
            "usuario.inexistente",
        )

        serialized_after = str(
            failed_log.after
        )

        serialized_before = str(
            failed_log.before
        )

        self.assertNotIn(
            fake_password,
            serialized_after,
        )

        self.assertNotIn(
            fake_password,
            serialized_before,
        )

        self.assertNotIn(
            "password",
            serialized_after.lower(),
        )