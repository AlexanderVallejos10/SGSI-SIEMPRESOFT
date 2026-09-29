from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.auditlog.models import AuditLog
from apps.organization.forms import AreaForm
from apps.organization.models import OrganizationalArea, Position, PositionAssignment
from apps.organization.services import assign_user_to_position, close_assignment, save_area


class OrganizationAreaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.editor = User.objects.create_superuser(username="editor", business_code="TEST-EDITOR")
        cls.reader = User.objects.create_user(username="reader", business_code="TEST-READER")
        cls.worker = User.objects.create_user(username="worker", business_code="TEST-WORKER")
        cls.root = Position.objects.create(code="ROOT", title="Gerencia")
        cls.position = Position.objects.create(code="DEV", title="Desarrollo", parent=cls.root, max_occupants=0)

    def setUp(self):
        self.client.force_login(self.editor)

    def area_data(self, **overrides):
        data = {
            "code": "", "name": "Tecnología", "description": "", "parent": "",
            "color": "#dcecf8", "sort_order": 100, "is_active": "on",
            "positions": [str(self.position.pk)],
        }
        data.update(overrides)
        return data

    def assign(self, position=None, primary=True):
        assignment = PositionAssignment(
            position=position or self.position, user=self.worker,
            start_date=timezone.localdate(), is_primary=primary,
        )
        return assign_user_to_position(assignment=assignment, actor=self.editor)

    def create_area(self):
        form = AreaForm(self.area_data())
        self.assertTrue(form.is_valid(), form.errors)
        return save_area(form=form, actor=self.editor)

    def test_empty_catalog_explains_configuration_and_lists_pending_positions(self):
        response = self.client.get(reverse("organization:areas"))
        self.assertContains(response, "Configure las áreas de la empresa")
        self.assertContains(response, "Desarrollo")
        self.assertContains(self.client.get(reverse("organization:chart")), "2 puestos sin área")

    def test_create_links_existing_position_and_preserves_reporting_line_and_assignment(self):
        assignment = self.assign()
        response = self.client.post(reverse("organization:area_create"), self.area_data())
        area = OrganizationalArea.objects.get(name="Tecnología")
        self.assertRedirects(response, reverse("organization:area_detail", args=[area.pk]))
        self.position.refresh_from_db()
        assignment.refresh_from_db()
        self.worker.refresh_from_db()
        self.assertEqual(self.position.area_id, area.pk)
        self.assertEqual(self.position.parent_id, self.root.pk)
        self.assertIsNone(assignment.end_date)
        self.assertEqual(self.worker.area, "Tecnología")
        self.assertEqual(area.code, "AREA-TECNOLOGIA")
        self.assertEqual(area.created_by, self.editor)

    def test_detail_counts_distinct_people_and_excludes_closed_and_inactive_positions(self):
        area = self.create_area()
        self.assign()
        extra = Position.objects.create(code="QA", title="Calidad", area=area)
        self.assign(extra, primary=False)
        Position.objects.create(code="VAC", title="Vacante", area=area)
        Position.objects.create(code="OFF", title="Archivado", area=area, is_active=False)
        PositionAssignment.objects.create(position=extra, user=self.reader, end_date=timezone.localdate(), is_primary=False)
        response = self.client.get(reverse("organization:area_detail", args=[area.pk]))
        self.assertEqual(response.context["position_count"], 3)
        self.assertEqual(response.context["member_count"], 1)
        self.assertEqual(response.context["vacant_count"], 1)
        self.assertContains(response, reverse("dashboard:user_profile", args=[self.worker.pk]))
        listing = self.client.get(reverse("organization:areas"))
        listed = next(a for a in listing.context["areas"] if a.pk == area.pk)
        self.assertEqual(listed.position_count, 3)
        self.assertEqual(listed.member_count, 1)

    def test_rename_area_updates_primary_profile_and_chart_link(self):
        area = self.create_area()
        self.assign()
        area.name = "Ingeniería"
        area.save()
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.area, "Ingeniería")
        response = self.client.get(reverse("organization:chart"))
        self.assertContains(response, reverse("organization:area_detail", args=[area.pk]))
        self.assertContains(response, "Ingeniería")

    def test_unlinking_position_clears_legacy_area_and_keeps_assignment(self):
        area = self.create_area()
        assignment = self.assign()
        form = AreaForm(self.area_data(code=area.code, positions=[]), instance=area)
        self.assertTrue(form.is_valid(), form.errors)
        save_area(form=form, actor=self.editor)
        self.position.refresh_from_db()
        self.worker.refresh_from_db()
        assignment.refresh_from_db()
        self.assertIsNone(self.position.area_id)
        self.assertEqual(self.worker.area, "")
        self.assertIsNone(assignment.end_date)

    def test_position_move_updates_primary_profile(self):
        self.create_area()
        self.assign()
        other = OrganizationalArea.objects.create(code="OPS", name="Operaciones")
        self.position.area = other
        self.position.title = "Especialista"
        self.position.save()
        self.worker.refresh_from_db()
        self.assertEqual((self.worker.area, self.worker.position), ("Operaciones", "Especialista"))

    def test_secondary_assignment_does_not_override_primary_profile(self):
        self.create_area()
        self.assign()
        other_area = OrganizationalArea.objects.create(code="SST", name="Seguridad y salud")
        secondary = Position.objects.create(code="SST-P", title="Comité", area=other_area)
        self.assign(secondary, primary=False)
        other_area.name = "SST"
        other_area.save()
        self.worker.refresh_from_db()
        self.assertEqual((self.worker.area, self.worker.position), ("Tecnología", "Desarrollo"))

    def test_closing_primary_clears_profile_text_and_keeps_history(self):
        self.create_area()
        assignment = self.assign()
        close_assignment(assignment=assignment, actor=self.editor)
        self.worker.refresh_from_db()
        self.assertEqual((self.worker.area, self.worker.position), ("", ""))
        self.assertTrue(PositionAssignment.objects.filter(pk=assignment.pk, end_date__isnull=False).exists())

    def test_changing_primary_assignment_to_secondary_clears_profile(self):
        self.create_area()
        assignment = self.assign()
        assignment.is_primary = False
        assignment.save()
        self.worker.refresh_from_db()
        self.assertEqual((self.worker.area, self.worker.position), ("", ""))

    def test_reassigning_primary_in_admin_synchronizes_both_users(self):
        self.create_area()
        assignment = self.assign()
        assignment.user = self.reader
        assignment.save()
        self.worker.refresh_from_db()
        self.reader.refresh_from_db()
        self.assertEqual((self.worker.area, self.worker.position), ("", ""))
        self.assertEqual((self.reader.area, self.reader.position), ("Tecnología", "Desarrollo"))

    def test_area_cycles_are_rejected(self):
        parent = OrganizationalArea.objects.create(code="P", name="Padre")
        child = OrganizationalArea.objects.create(code="C", name="Hija", parent=parent)
        parent.parent = child
        with self.assertRaises(ValidationError):
            parent.full_clean()
        child.parent = child
        with self.assertRaises(ValidationError):
            child.full_clean()

    def test_active_positions_prevent_area_deactivation(self):
        area = self.create_area()
        form = AreaForm(self.area_data(code=area.code, is_active=""), instance=area)
        self.assertFalse(form.is_valid())
        self.assertIn("is_active", form.errors)

    def test_cannot_link_positions_from_another_area_through_area_form(self):
        self.create_area()
        form = AreaForm(self.area_data(name="Otra"))
        self.assertFalse(form.is_valid())
        self.assertIn("positions", form.errors)

    def test_position_claimed_after_validation_is_not_stolen(self):
        form = AreaForm(self.area_data())
        self.assertTrue(form.is_valid(), form.errors)
        other = OrganizationalArea.objects.create(code="OTHER", name="Otra")
        self.position.area = other
        self.position.save()
        with self.assertRaises(ValidationError):
            save_area(form=form, actor=self.editor)
        self.position.refresh_from_db()
        self.assertEqual(self.position.area_id, other.pk)
        self.assertFalse(OrganizationalArea.objects.filter(name="Tecnología").exists())

    def test_readers_can_view_but_cannot_modify_areas(self):
        area = self.create_area()
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(reverse("organization:areas")).status_code, 200)
        self.assertEqual(self.client.get(reverse("organization:area_detail", args=[area.pk])).status_code, 200)
        self.assertNotContains(self.client.get(reverse("organization:areas")), "Nueva área")
        self.assertEqual(self.client.post(reverse("organization:area_create"), self.area_data()).status_code, 403)
        self.assertEqual(self.client.post(reverse("organization:area_edit", args=[area.pk]), self.area_data()).status_code, 403)

    def test_area_pages_require_login(self):
        area = self.create_area()
        self.client.logout()
        for url in [reverse("organization:areas"), reverse("organization:area_detail", args=[area.pk])]:
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_area_creation_and_position_link_are_audited_with_actor(self):
        self.client.post(reverse("organization:area_create"), self.area_data())
        area = OrganizationalArea.objects.get(name="Tecnología")
        log = AuditLog.objects.get(entity="organization.organizationalarea", entity_id=area.code, action="CREATE")
        self.assertEqual(log.user_id, self.editor.pk)
        log = AuditLog.objects.filter(entity="organization.position", entity_id=self.position.code, action="UPDATE").latest("occurred_at")
        self.assertEqual(log.before["area"], None)
        self.assertEqual(log.after["area"], str(area.pk))
        self.assertEqual(log.user_id, self.editor.pk)

    def test_new_position_can_start_with_selected_area(self):
        area = self.create_area()
        response = self.client.get(reverse("organization:position_create"), {"area": str(area.pk)})
        self.assertEqual(response.context["form"].initial["area"], area)

    def test_assignment_failure_rolls_back_previous_primary(self):
        self.create_area()
        primary = self.assign()
        full = Position.objects.create(code="FULL", title="Ocupado")
        PositionAssignment.objects.create(position=full, user=self.reader)
        with self.assertRaises(ValidationError):
            self.assign(full)
        primary.refresh_from_db()
        self.worker.refresh_from_db()
        self.assertIsNone(primary.end_date)
        self.assertEqual(self.worker.position, "Desarrollo")

    def test_quick_create_failure_does_not_leave_an_unassigned_account(self):
        full = Position.objects.create(code="FULL", title="Ocupado")
        PositionAssignment.objects.create(position=full, user=self.reader)
        response = self.client.post(reverse("organization:quick_user_create", args=[full.pk]), {
            "username": "new-worker", "business_code": "NEW-WORKER", "start_date": timezone.localdate().isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "capacidad activa")
        self.assertFalse(get_user_model().objects.filter(username="new-worker").exists())
