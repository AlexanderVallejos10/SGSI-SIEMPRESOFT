from django.contrib import admin

from .models import ManagementReview, ReviewDecision, RiskAcceptance


class DecisionInline(admin.TabularInline):
    model = ReviewDecision
    extra = 0


@admin.register(ManagementReview)
class ManagementReviewAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "review_date", "status", "approved_by", "approved_at")
    list_filter = ("status",)
    inlines = [DecisionInline]
    readonly_fields = ("inputs", "inputs_at", "approved_by", "approved_at")


@admin.register(RiskAcceptance)
class RiskAcceptanceAdmin(admin.ModelAdmin):
    list_display = ("risk", "residual_level", "decision", "decided_by", "decided_at", "is_current")
    list_filter = ("decision", "is_current", "residual_level")

    def has_change_permission(self, request, obj=None):
        return False  # una aceptación no se edita: se registra una nueva
