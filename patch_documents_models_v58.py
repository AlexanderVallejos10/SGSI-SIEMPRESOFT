from pathlib import Path

path = Path("apps/documents/models.py")
text = path.read_text(encoding="utf-8")

backup = Path("apps/documents/models_before_v58.bak")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

old_status = '''class LifecycleStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    REVIEW = "review", "En revisión"
    ACTIVE = "active", "Vigente / Activo"
    INACTIVE = "inactive", "Inactivo"
    OBSOLETE = "obsolete", "Obsoleto"
'''

new_status = '''class LifecycleStatus(models.TextChoices):
    UNKNOWN = "unknown", "Estado no determinado"
    DRAFT = "draft", "Borrador"
    REVIEW = "review", "En revisión"
    ACTIVE = "active", "Vigente / Activo"
    INACTIVE = "inactive", "Inactivo"
    OBSOLETE = "obsolete", "Obsoleto"
'''

if old_status in text:
    text = text.replace(old_status, new_status, 1)
elif 'UNKNOWN = "unknown", "Estado no determinado"' not in text:
    raise SystemExit(
        "ERROR: no se encontró el bloque esperado de LifecycleStatus."
    )

doc_start = text.find("class Document(TraceableModel):")
ver_start = text.find("class DocumentVersion(TraceableModel):")
if doc_start == -1 or ver_start == -1 or ver_start <= doc_start:
    raise SystemExit("ERROR: no se localizaron Document/DocumentVersion.")

doc_block = text[doc_start:ver_start]

code_block = '''    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )
'''

code_with_identity = code_block + '''
    source_identity_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text=(
            "Huella estable de la identidad documental importada. "
            "Permite reejecutar la promoción sin duplicar documentos."
        ),
    )
'''

if "source_identity_key = models.CharField(" not in doc_block:
    if code_block not in doc_block:
        raise SystemExit(
            "ERROR: no se encontró el campo code esperado en Document."
        )
    doc_block = doc_block.replace(
        code_block,
        code_with_identity,
        1,
    )

owner_old = '''    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_documents",
    )
'''

owner_new = '''    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="owned_documents",
        help_text=(
            "Responsable documental. Puede quedar pendiente "
            "durante una importación histórica."
        ),
    )
'''

if "Responsable documental. Puede quedar pendiente" not in doc_block:
    if owner_old not in doc_block:
        raise SystemExit(
            "ERROR: no se encontró el campo owner esperado en Document."
        )
    doc_block = doc_block.replace(owner_old, owner_new, 1)

doc_block = doc_block.replace(
    "default=LifecycleStatus.DRAFT,",
    "default=LifecycleStatus.UNKNOWN,",
    1,
)

text = text[:doc_start] + doc_block + text[ver_start:]

ver_start = text.find("class DocumentVersion(TraceableModel):")
evidence_start = text.find("class Evidence(", ver_start)
if evidence_start == -1:
    raise SystemExit(
        "ERROR: no se encontró el inicio de Evidence después de DocumentVersion."
    )

ver_block = text[ver_start:evidence_start]
ver_block = ver_block.replace(
    "default=LifecycleStatus.DRAFT,",
    "default=LifecycleStatus.UNKNOWN,",
    1,
)
text = text[:ver_start] + ver_block + text[evidence_start:]

promotion_import = (
    "from .models_promotion import "
    "DocumentImportIssue, DocumentVersionRepresentation\n"
)

if promotion_import not in text:
    if not text.endswith("\n"):
        text += "\n"
    text += "\n" + promotion_import

path.write_text(text, encoding="utf-8")

print("OK: models.py actualizado.")
print(f"Backup: {backup}")
print("Cambios esperados:")
print("- LifecycleStatus.UNKNOWN")
print("- Document.source_identity_key")
print("- Document.owner nullable")
print("- Document.status default UNKNOWN")
print("- DocumentVersion.status default UNKNOWN")
print("- Import de modelos de promoción")
