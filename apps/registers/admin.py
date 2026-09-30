from django.contrib import admin

from .models import RegisterEntry, RegisterImport


@admin.register(RegisterEntry)
class RegisterEntryAdmin(admin.ModelAdmin):
    list_display = ("register", "year", "section", "order", "updated_at")
    list_filter = ("register", "year", "section")


@admin.register(RegisterImport)
class RegisterImportAdmin(admin.ModelAdmin):
    list_display = ("register", "year", "file_name", "rows", "replaced", "created_by", "created_at")
    list_filter = ("register",)
