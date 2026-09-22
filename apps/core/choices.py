from django.db import models


class Classification(models.TextChoices):
    PUBLIC = "public", "Público"
    INTERNAL = "internal", "Uso interno"
    RESTRICTED = "restricted", "Restringido"
    CONFIDENTIAL = "confidential", "Confidencial"


class LifecycleStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    REVIEW = "review", "En revisión"
    ACTIVE = "active", "Vigente / Activo"
    INACTIVE = "inactive", "Inactivo"
    OBSOLETE = "obsolete", "Obsoleto"
