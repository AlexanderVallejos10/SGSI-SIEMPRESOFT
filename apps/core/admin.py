from django.contrib import admin


class NoDeleteAdminMixin:
    """
    Impide la eliminación física desde Django Admin.

    Los registros del SGSI deben cambiar de estado
    mediante sus flujos funcionales:
    cerrado, obsoleto, inactivo, archivado, etc.
    """

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions