from django.contrib import admin

from .models import Context42Document, Context42DocumentVersion, InterestedPartyRow, LegalRequirementRow


@admin.register(Context42Document)
class Context42DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "sort_order", "is_active", "updated_at")
    search_fields = ("title", "slug")


@admin.register(Context42DocumentVersion)
class Context42DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("document", "version_label", "original_name", "is_current", "created_at")
    list_filter = ("document", "is_current")
    search_fields = ("original_name", "version_label", "document__title")


@admin.register(InterestedPartyRow)
class InterestedPartyRowAdmin(admin.ModelAdmin):
    list_display = ("party_name", "source_row", "version")
    search_fields = ("party_name", "need", "expectation")


@admin.register(LegalRequirementRow)
class LegalRequirementRowAdmin(admin.ModelAdmin):
    list_display = ("item_no", "promulgated_by", "responsible", "status")
    search_fields = ("requirement", "promulgated_by", "responsible", "status")
