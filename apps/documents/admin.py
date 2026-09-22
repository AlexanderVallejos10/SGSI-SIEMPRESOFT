from django.contrib import admin

from apps.core.admin import NoDeleteAdminMixin

from .models import (
    Document,
    DocumentVersion,
    Evidence,
    SGSISection,
    SourceArtifact,
    SourcePackage,
    SourceArtifactClassification,
    DocumentVersionRepresentation,
    DocumentImportIssue,
    DocumentSectionAssignment,
)


@admin.register(SGSISection)
class SGSISectionAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "code",
        "title",
        "parent",
        "manual_version",
        "sort_order",
        "is_active",
    )

    search_fields = (
        "code",
        "title",
        "description",
    )

    list_filter = (
        "manual_version",
        "is_active",
    )

    ordering = (
        "sort_order",
        "code",
    )


@admin.register(SourcePackage)
class SourcePackageAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "code",
        "original_name",
        "size_bytes",
        "checksum_sha256",
        "status",
        "received_at",
    )

    search_fields = (
        "code",
        "original_name",
        "original_path",
        "checksum_sha256",
    )

    list_filter = (
        "status",
    )

    ordering = (
        "original_name",
    )


@admin.register(SourceArtifact)
class SourceArtifactAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "code",
        "original_name",
        "source_package",
        "source_archive",
        "extension",
        "size_bytes",
        "quality_status",
        "source_verified",
        "duplicate_of",
    )

    search_fields = (
        "code",
        "original_name",
        "original_path",
        "source_archive",
        "checksum_sha256",
    )

    list_filter = (
        "source_kind",
        "quality_status",
        "source_verified",
        "extension",
    )

    ordering = (
        "source_archive",
        "original_path",
        "original_name",
    )

    autocomplete_fields = (
        "source_package",
        "duplicate_of",
    )


@admin.register(Document)
class DocumentAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "code",
        "title",
        "category",
        "document_type",
        "classification",
        "status",
        "next_review_at",
    )

    search_fields = (
        "code",
        "title",
        "category",
        "document_type",
    )

    list_filter = (
        "classification",
        "status",
        "management_system",
    )

    filter_horizontal = (
        "sgsi_sections",
    )


@admin.register(DocumentVersion)
class DocumentVersionAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "document",
        "version",
        "issue_date",
        "status",
        "author",
        "reviewer",
        "approver",
        "source_artifact",
    )

    search_fields = (
        "document__code",
        "document__title",
        "version",
        "checksum_sha256",
        "source_artifact__original_name",
    )

    list_filter = (
        "status",
        "issue_date",
    )

    autocomplete_fields = (
        "document",
        "author",
        "reviewer",
        "approver",
        "source_artifact",
    )


@admin.register(Evidence)
class EvidenceAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "code",
        "description",
        "evidence_date",
        "classification",
        "document_version",
        "source_artifact",
    )

    search_fields = (
        "code",
        "description",
        "source",
        "checksum_sha256",
        "source_artifact__original_name",
    )

    list_filter = (
        "classification",
        "evidence_date",
    )

    autocomplete_fields = (
        "document_version",
        "source_artifact",
    )

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

