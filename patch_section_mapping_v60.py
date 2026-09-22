from pathlib import Path

models_file = Path("apps/documents/models.py")
dp_file = Path("apps/core/deletion_protection.py")
admin_file = Path("apps/documents/admin.py")

models_text = models_file.read_text(encoding="utf-8")
dp_text = dp_file.read_text(encoding="utf-8")
admin_text = admin_file.read_text(encoding="utf-8")

for original, backup in (
    (models_file, Path("apps/documents/models_before_section_mapping.bak")),
    (dp_file, Path("apps/core/deletion_protection_before_section_mapping.bak")),
    (admin_file, Path("apps/documents/admin_before_section_mapping.bak")),
):
    if not backup.exists():
        backup.write_text(original.read_text(encoding="utf-8"), encoding="utf-8")

model_import = "from .models_mapping import DocumentSectionAssignment\n"
if model_import not in models_text:
    models_text = models_text.rstrip() + "\n\n" + model_import

label = '        "documents.documentsectionassignment",\n'
anchor = '        "documents.documentimportissue",\n'
if label.strip() not in dp_text:
    if anchor not in dp_text:
        raise SystemExit("ERROR: no se encontró documents.documentimportissue en deletion_protection.py")
    dp_text = dp_text.replace(anchor, anchor + label, 1)

import_anchor = "    DocumentImportIssue,\n"
admin_import = "    DocumentSectionAssignment,\n"
if "DocumentSectionAssignment" not in admin_text:
    if import_anchor not in admin_text:
        raise SystemExit("ERROR: no se encontró DocumentImportIssue en el import de admin.py")
    admin_text = admin_text.replace(import_anchor, import_anchor + admin_import, 1)

admin_block = """

@admin.register(DocumentSectionAssignment)
class DocumentSectionAssignmentAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "document",
        "section",
        "method",
        "confidence",
        "rule_version",
        "is_active",
    )

    search_fields = (
        "document__code",
        "document__title",
        "section__code",
        "section__title",
        "reason",
    )

    list_filter = (
        "method",
        "rule_version",
        "is_active",
        "section",
    )

    autocomplete_fields = (
        "document",
        "section",
    )
"""

if "@admin.register(DocumentSectionAssignment)" not in admin_text:
    admin_text = admin_text.rstrip() + admin_block + "\n"

models_file.write_text(models_text, encoding="utf-8")
dp_file.write_text(dp_text, encoding="utf-8")
admin_file.write_text(admin_text, encoding="utf-8")

print("OK: capa de asignación SGSI registrada.")
print("- models.py importa DocumentSectionAssignment")
print("- deletion_protection protege DocumentSectionAssignment")
print("- admin.py registra DocumentSectionAssignment con NoDeleteAdminMixin")
