from pathlib import Path

models_file = Path("apps/controls/models.py")
admin_file = Path("apps/controls/admin.py")
delete_file = Path("apps/core/deletion_protection.py")

models_text = models_file.read_text(encoding="utf-8")
admin_text = admin_file.read_text(encoding="utf-8")
delete_text = delete_file.read_text(encoding="utf-8")

for source, backup in (
    (models_file, Path("apps/controls/models_before_iso_v61.bak")),
    (admin_file, Path("apps/controls/admin_before_iso_v61.bak")),
    (delete_file, Path("apps/core/deletion_protection_before_iso_v61.bak")),
):
    if not backup.exists():
        backup.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

model_import = (
    "from .models_iso import "
    "ControlSupportReference, ISOClause, ISODataQualityIssue, ISORequirement\n"
)
if model_import not in models_text:
    models_text = models_text.rstrip() + "\n\n" + model_import

labels = [
    '        "controls.isoclause",\n',
    '        "controls.isorequirement",\n',
    '        "controls.controlsupportreference",\n',
    '        "controls.isodataqualityissue",\n',
]
anchor = '        "controls.controlevidence",\n'
if anchor not in delete_text:
    raise SystemExit(
        "ERROR: no se encontró controls.controlevidence en deletion_protection.py"
    )

addition = "".join(label for label in labels if label.strip() not in delete_text)
if addition:
    delete_text = delete_text.replace(anchor, anchor + addition, 1)

admin_append = """
from .models_iso import (
    ControlSupportReference,
    ISOClause,
    ISODataQualityIssue,
    ISORequirement,
)


@admin.register(ISOClause)
class ISOClauseAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "framework",
        "code",
        "title",
        "parent",
        "level",
        "source_sheet",
        "source_row",
        "active",
    )
    search_fields = (
        "code",
        "title",
        "framework__code",
        "framework__name",
    )
    list_filter = (
        "framework",
        "level",
        "active",
    )
    autocomplete_fields = (
        "framework",
        "parent",
        "source_artifact",
    )


@admin.register(ISORequirement)
class ISORequirementAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "clause",
        "source_label",
        "source_row",
        "is_clause_heading",
        "source_artifact",
    )
    search_fields = (
        "clause__code",
        "description",
        "supporting_reference",
        "source_label",
    )
    list_filter = (
        "is_clause_heading",
        "clause__framework",
    )
    autocomplete_fields = (
        "clause",
        "source_artifact",
    )


@admin.register(ControlSupportReference)
class ControlSupportReferenceAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "control",
        "source_row",
        "raw_control_code",
        "source_artifact",
    )
    search_fields = (
        "control__code",
        "control__name",
        "supporting_reference",
        "raw_control_name",
    )
    autocomplete_fields = (
        "control",
        "source_artifact",
    )


@admin.register(ISODataQualityIssue)
class ISODataQualityIssueAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "issue_type",
        "severity",
        "source_sheet",
        "source_row",
        "resolved",
    )
    search_fields = (
        "code",
        "description",
        "resolution_notes",
    )
    list_filter = (
        "issue_type",
        "severity",
        "resolved",
    )
    autocomplete_fields = (
        "source_artifact",
    )
"""

if "@admin.register(ISOClause)" not in admin_text:
    admin_text = admin_text.rstrip() + "\n\n" + admin_append.strip() + "\n"

models_file.write_text(models_text, encoding="utf-8")
admin_file.write_text(admin_text, encoding="utf-8")
delete_file.write_text(delete_text, encoding="utf-8")

print("OK: modelos ISO registrados en controls.")
print("- ISOClause")
print("- ISORequirement")
print("- ControlSupportReference")
print("- ISODataQualityIssue")
print("- protección física actualizada")
print("- Django Admin actualizado")
