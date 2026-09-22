from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Context42DocumentKind(models.TextChoices):
    INTERESTED = "interested", "Partes interesadas"
    LEGAL = "legal", "Lista de requisitos legales"


class Context42Document(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=Context42DocumentKind.choices)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "title")

    def __str__(self):
        return self.title


class Context42DocumentVersion(models.Model):
    document = models.ForeignKey(Context42Document, related_name="versions", on_delete=models.CASCADE)
    file = models.FileField(upload_to="context42/")
    original_name = models.CharField(max_length=255)
    version_label = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)
    is_current = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="context42_versions_created", on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="context42_versions_updated", on_delete=models.SET_NULL)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.document.title} - {self.version_label or self.original_name}"

    @property
    def extension(self):
        name = self.original_name or self.file.name
        return name.lower().rsplit('.', 1)[-1] if '.' in name else ''


class InterestedPartyRow(models.Model):
    version = models.ForeignKey(Context42DocumentVersion, related_name="party_rows", on_delete=models.CASCADE)
    source_row = models.PositiveIntegerField(null=True, blank=True)
    party_name = models.CharField(max_length=180, db_index=True)
    need = models.TextField()
    expectation = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("source_row", "party_name", "id")


class LegalRequirementRow(models.Model):
    version = models.ForeignKey(Context42DocumentVersion, related_name="legal_rows", on_delete=models.CASCADE)
    source_row = models.PositiveIntegerField(null=True, blank=True)
    item_no = models.CharField(max_length=30, blank=True)
    requirement = models.TextField()
    promulgated_by = models.CharField(max_length=200, blank=True)
    location = models.TextField(blank=True)
    responsible = models.CharField(max_length=200, blank=True)
    stakeholders = models.TextField(blank=True)
    status = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("source_row", "id")
