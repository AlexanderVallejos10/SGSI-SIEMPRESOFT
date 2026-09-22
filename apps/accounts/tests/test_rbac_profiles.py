from django.apps import apps
from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import (
    RequestFactory,
    TestCase,
)
from django.urls import reverse

from apps.accounts.business_permissions import (
    sync_business_permissions,
)
from apps.accounts.models import User
from apps.accounts.rbac import sync_rbac_roles
from apps.core.deletion_protection import (
    PROTECTED_MODEL_LABELS,
)


class RBACProfileTests(TestCase):
    """
    Valida que los perfiles principales del SGSI
    tengan acceso únicamente a las funciones que
    corresponden a su rol.
    """

    @classmethod
    def setUpTestData(cls):
        sync_rbac_roles()
        sync_business_permissions()

        cls.reader = cls.create_user_with_role(
            username="lector.test",
            code="USR-RBAC-001",
            role="Consulta / Lector",
        )

        cls.asset_manager = (
            cls.create_user_with_role(
                username="activos.test",
                code="USR-RBAC-002",
                role="Responsable de Activos",
            )
        )

        cls.auditor = cls.create_user_with_role(
            username="auditor.test",
            code="USR-RBAC-003",
            role="Auditor",
        )

        cls.factory = RequestFactory()

    @classmethod
    def create_user_with_role(
        cls,
        username,
        code,
        role,
    ):
        user = User.objects.create_user(
            username=username,
            business_code=code,
            email=f"{username}@siempresoft.local",
            password="Temporal123!",
            is_staff=True,
        )

        group = Group.objects.get(
            name=role,
        )

        user.groups.add(group)

        return user

    def test_consulta_lector_permissions(self):
        """
        El lector puede consultar,
        pero no modificar información.
        """

        user = self.reader

        self.assertTrue(
            user.has_perm(
                "documents.view_document"
            )
        )

        self.assertTrue(
            user.has_perm(
                "controls.view_control"
            )
        )

        self.assertTrue(
            user.has_perm(
                "risks.view_risk"
            )
        )

        self.assertFalse(
            user.has_perm(
                "documents.change_document"
            )
        )

        self.assertFalse(
            user.has_perm(
                "assets.view_asset"
            )
        )

        self.assertFalse(
            user.has_perm(
                "risks.close_risk"
            )
        )

        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "admin:documents_document_changelist"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        response = self.client.get(
            reverse(
                "admin:assets_asset_changelist"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_responsable_activos_permissions(self):
        """
        Responsable de Activos puede administrar
        activos pero no riesgos.
        """

        user = self.asset_manager

        self.assertTrue(
            user.has_perm(
                "assets.view_asset"
            )
        )

        self.assertTrue(
            user.has_perm(
                "assets.add_asset"
            )
        )

        self.assertTrue(
            user.has_perm(
                "assets.change_asset"
            )
        )

        self.assertTrue(
            user.has_perm(
                "assets.assign_asset"
            )
        )

        self.assertTrue(
            user.has_perm(
                "assets.return_asset"
            )
        )

        self.assertTrue(
            user.has_perm(
                "assets.replace_asset"
            )
        )

        self.assertFalse(
            user.has_perm(
                "assets.delete_asset"
            )
        )

        self.assertFalse(
            user.has_perm(
                "risks.change_risk"
            )
        )

        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "admin:assets_asset_changelist"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        response = self.client.get(
            reverse(
                "admin:risks_risk_changelist"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_auditor_permissions(self):
        """
        Auditor puede consultar información general
        y administrar el módulo de auditoría,
        pero no modificar activos.
        """

        user = self.auditor

        self.assertTrue(
            user.has_perm(
                "assets.view_asset"
            )
        )

        self.assertFalse(
            user.has_perm(
                "assets.change_asset"
            )
        )

        self.assertTrue(
            user.has_perm(
                "assurance.view_audit"
            )
        )

        self.assertTrue(
            user.has_perm(
                "assurance.add_audit"
            )
        )

        self.assertTrue(
            user.has_perm(
                "assurance.change_audit"
            )
        )

        self.assertTrue(
            user.has_perm(
                "assurance.close_audit"
            )
        )

        self.assertTrue(
            user.has_perm(
                "assurance.close_finding"
            )
        )

        self.assertFalse(
            user.has_perm(
                "assurance.delete_audit"
            )
        )

        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "admin:assets_asset_changelist"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        response = self.client.get(
            reverse(
                "admin:assets_asset_add"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        response = self.client.get(
            reverse(
                "admin:assurance_audit_add"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_protected_models_have_no_admin_delete(self):
        """
        Todos los modelos críticos protegidos deben
        tener deshabilitado DELETE en Django Admin.
        """

        request = self.factory.get(
            "/admin/"
        )

        request.user = self.auditor

        for model_label in (
            PROTECTED_MODEL_LABELS
        ):
            app_label, model_name = (
                model_label.split(".", 1)
            )

            model = apps.get_model(
                app_label,
                model_name,
            )

            self.assertIn(
                model,
                admin.site._registry,
                msg=(
                    f"{model_label} no está "
                    "registrado en Django Admin"
                ),
            )

            model_admin = (
                admin.site._registry[model]
            )

            self.assertFalse(
                model_admin.has_delete_permission(
                    request
                ),
                msg=(
                    "DELETE sigue habilitado para "
                    f"{model_label}"
                ),
            )

    def test_no_role_has_delete_permissions(self):
        """
        Ningún rol funcional del SGSI debe recibir
        permisos delete_*.
        """

        for group in Group.objects.all():
            delete_permissions = (
                group.permissions.filter(
                    codename__startswith="delete_"
                )
            )

            self.assertFalse(
                delete_permissions.exists(),
                msg=(
                    f"El rol '{group.name}' tiene "
                    "permisos DELETE."
                ),
            )