from pathlib import Path

models_file = Path("apps/controls/models.py")
admin_file = Path("apps/controls/admin.py")
delete_file = Path("apps/core/deletion_protection.py")

models_text = models_file.read_text(encoding="utf-8")
admin_text = admin_file.read_text(encoding="utf-8")
delete_text = delete_file.read_text(encoding="utf-8")

for source, backup in (
    (models_file, Path("apps/controls/models_before_linking_v61c.bak")),
    (admin_file, Path("apps/controls/admin_before_linking_v61c.bak")),
    (delete_file, Path("apps/core/deletion_protection_before_linking_v61c.bak")),
):
    if not backup.exists():
        backup.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

link_model_path = Path("apps/controls/models_linking.py")
if not link_model_path.exists():
    raise SystemExit("ERROR: falta apps/controls/models_linking.py")

model_import = "from .models_linking import ControlDocumentAssignment\n"
if model_import not in models_text:
    models_text = models_text.rstrip() + "\n\n" + model_import

label = '        "controls.controldocumentassignment",\n'
anchor = '        "controls.isodataqualityissue",\n'
if label.strip() not in delete_text:
    if anchor not in delete_text:
        raise SystemExit(
            "ERROR: no se encontró controls.isodataqualityissue "
            "en deletion_protection.py"
        )
    delete_text = delete_text.replace(anchor, anchor + label, 1)

admin_append = '''

from .models_linking import ControlDocumentAssignment


@admin.register(ControlDocumentAssignment)
class ControlDocumentAssignmentAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "control",
        "document",
        "method",
        "confidence",
        "rule_version",
        "is_active",
    )

    search_fields = (
        "control__code",
        "control__name",
        "document__code",
        "document__title",
        "matched_fragment",
        "matched_alias",
        "reason",
    )

    list_filter = (
        "method",
        "rule_version",
        "is_active",
    )

    raw_id_fields = (
        "control",
    )

    autocomplete_fields = (
        "document",
        "support_reference",
    )
'''

if "@admin.register(ControlDocumentAssignment)" not in admin_text:
    admin_text = admin_text.rstrip() + admin_append + "\n"

models_file.write_text(models_text, encoding="utf-8")
admin_file.write_text(admin_text, encoding="utf-8")
delete_file.write_text(delete_text, encoding="utf-8")

print("OK: capa auditable Control ↔ Document registrada.")
print("- ControlDocumentAssignment")
print("- protección física actualizada")
print("- Django Admin actualizado")
