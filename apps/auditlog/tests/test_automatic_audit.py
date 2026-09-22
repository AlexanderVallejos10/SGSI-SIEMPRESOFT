from django.test import TestCase

from apps.accounts.models import User
from apps.auditlog.context import (
    AuditRequestContext,
    reset_audit_context,
    set_audit_context,
)
from apps.auditlog.models import AuditLog
from apps.risks.models import Risk, RiskStatus


class AutomaticAuditLogTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            username="audit.test",
            business_code="USR-TEST-001",
            email="audit.test@siempresoft.local",
            password="Temporal123!",
        )

    def test_create_and_update_risk_are_audited(self):
        token = set_audit_context(
            AuditRequestContext(
                user=self.actor,
                ip_address="127.0.0.1",
                session_key="test-session",
            )
        )

        try:
            risk = Risk.objects.create(
                code="R-TEST-001",
                process="Proceso de prueba",
                scenario="Escenario utilizado para probar la bitácora",
                owner=self.actor,
            )

            create_log = AuditLog.objects.get(
                action="CREATE",
                entity="risks.risk",
                entity_id="R-TEST-001",
            )

            self.assertEqual(
                create_log.user_id,
                self.actor.id,
            )

            self.assertEqual(
                create_log.ip_address,
                "127.0.0.1",
            )

            self.assertEqual(
                create_log.session_key,
                "test-session",
            )

            self.assertEqual(
                create_log.after["status"],
                RiskStatus.IDENTIFIED,
            )

            self.assertEqual(
                risk.created_by_id,
                self.actor.id,
            )

            self.assertEqual(
                risk.updated_by_id,
                self.actor.id,
            )

            risk.status = RiskStatus.TREATMENT
            risk.save()

            update_log = AuditLog.objects.get(
                action="UPDATE",
                entity="risks.risk",
                entity_id="R-TEST-001",
            )

            self.assertEqual(
                update_log.before["status"],
                RiskStatus.IDENTIFIED,
            )

            self.assertEqual(
                update_log.after["status"],
                RiskStatus.TREATMENT,
            )

            self.assertEqual(
                update_log.user_id,
                self.actor.id,
            )

        finally:
            reset_audit_context(token)

    def test_password_is_never_written_to_audit_log(self):
        token = set_audit_context(
            AuditRequestContext(
                user=self.actor,
                ip_address="127.0.0.1",
                session_key="password-test",
            )
        )

        try:
            user = User.objects.create_user(
                username="password.audit.test",
                business_code="USR-TEST-002",
                email="password.audit@siempresoft.local",
                password="SuperSecret123!",
            )

            log = AuditLog.objects.get(
                action="CREATE",
                entity="accounts.user",
                entity_id="USR-TEST-002",
            )

            self.assertEqual(
                log.after["password"],
                "<redacted>",
            )

            serialized_log = str(log.after)

            self.assertNotIn(
                "SuperSecret123!",
                serialized_log,
            )

            self.assertNotIn(
                user.password,
                serialized_log,
            )

        finally:
            reset_audit_context(token)