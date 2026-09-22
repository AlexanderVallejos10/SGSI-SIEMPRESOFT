from pathlib import Path

dp = Path("apps/core/deletion_protection.py")
admin_file = Path("apps/documents/admin.py")

dp_text = dp.read_text(encoding="utf-8")
admin_text = admin_file.read_text(encoding="utf-8")

dp_backup = Path("apps/core/deletion_protection_before_v59.bak")
admin_backup = Path("apps/documents/admin_before_v59.bak")

if not dp_backup.exists():
    dp_backup.write_text(dp_text, encoding="utf-8")
if not admin_backup.exists():
    admin_backup.write_text(admin_text, encoding="utf-8")

labels = [
    '        "documents.sourceartifactclassification",\n',
    '        "documents.documentversionrepresentation",\n',
    '        "documents.documentimportissue",\n',
]

anchor = '        "documents.sourcepackage",\n'
if anchor not in dp_text:
    raise SystemExit(
        "ERROR: no se encontró documents.sourcepackage en deletion_protection.py"
    )

insertion = ""
for label in labels:
    if label.strip() not in dp_text:
        insertion += label

if insertion:
    dp_text = dp_text.replace(anchor, anchor + insertion, 1)

import_anchor = "    SourcePackage,\n"
if import_anchor not in admin_text:
    raise SystemExit(
        "ERROR: no se encontró SourcePackage en el import de admin.py"
    )

needed_imports = [
    "    SourceArtifactClassification,\n",
    "    DocumentVersionRepresentation,\n",
    "    DocumentImportIssue,\n",
]

admin_insertion = ""
for item in needed_imports:
    token = item.strip().rstrip(",")
    if token not in admin_text:
        admin_insertion += item

if admin_insertion:
    admin_text = admin_text.replace(
        import_anchor,
        import_anchor + admin_insertion,
        1,
    )

classification_admin = '''

@admin.register(SourceArtifactClassification)
class SourceArtifactClassificationAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "artifact",
        "family_hint",
        "lifecycle_hint",
        "sgsi_relevance",
        "area_hint",
        "confidence",
        "rule_version",
    )

    search_fields = (
        "artifact__code",
        "artifact__original_name",
        "artifact__original_path",
        "area_hint",
        "classification_reason",
    )

    list_filter = (
        "family_hint",
        "lifecycle_hint",
        "sgsi_relevance",
        "is_document_candidate",
        "is_evidence_candidate",
        "is_dashboard_candidate",
        "rule_version",
    )

    autocomplete_fields = (
        "artifact",
    )


@admin.register(DocumentVersionRepresentation)
class DocumentVersionRepresentationAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "document_version",
        "representation_type",
        "is_primary",
        "source_artifact",
    )

    search_fields = (
        "document_version__document__code",
        "document_version__document__title",
        "document_version__version",
        "source_artifact__code",
        "source_artifact__original_name",
    )

    list_filter = (
        "representation_type",
        "is_primary",
    )

    autocomplete_fields = (
        "document_version",
        "source_artifact",
    )


@admin.register(DocumentImportIssue)
class DocumentImportIssueAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "code",
        "issue_type",
        "status",
        "title",
        "version_label",
        "document",
    )

    search_fields = (
        "code",
        "title",
        "description",
        "group_key",
        "document__code",
        "document__title",
    )

    list_filter = (
        "issue_type",
        "status",
    )

    autocomplete_fields = (
        "document",
        "source_artifacts",
    )
'''

if "@admin.register(SourceArtifactClassification)" not in admin_text:
    admin_text = admin_text.rstrip() + classification_admin + "\n"

dp.write_text(dp_text, encoding="utf-8")
admin_file.write_text(admin_text, encoding="utf-8")

print("OK: protección y admin actualizados.")
print(f"Backup protección: {dp_backup}")
print(f"Backup admin: {admin_backup}")
print("Modelos nuevos protegidos:")
print("- SourceArtifactClassification")
print("- DocumentVersionRepresentation")
print("- DocumentImportIssue")
