from pathlib import Path

path = Path("apps/documents/models.py")
text = path.read_text(encoding="utf-8")
backup = Path("apps/documents/models_before_v58b.bak")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")
lines = text.splitlines(keepends=True)

def find_line(prefix, start=0):
    for i in range(start, len(lines)):
        if lines[i].startswith(prefix):
            return i
    return -1

def find_class(name, start=0):
    return find_line(f"class {name}", start)

def find_block_end(start_idx):
    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith("class "):
            return i
    return len(lines)

# 1) LifecycleStatus.UNKNOWN
lifecycle_idx = find_class("LifecycleStatus(")
if lifecycle_idx == -1:
    raise SystemExit("ERROR: no se encontró LifecycleStatus.")
lifecycle_end = find_block_end(lifecycle_idx)
if not any('UNKNOWN = "unknown"' in lines[i] for i in range(lifecycle_idx, lifecycle_end)):
    lines.insert(lifecycle_idx + 1, '    UNKNOWN = "unknown", "Estado no determinado"\n')

# Recalcular índices después de inserciones.
doc_idx = find_class("Document(")
ver_idx = find_class("DocumentVersion(")
evidence_idx = find_class("Evidence(")
if min(doc_idx, ver_idx, evidence_idx) == -1:
    raise SystemExit("ERROR: no se localizaron Document/DocumentVersion/Evidence.")

# 2) Document.source_identity_key
has_identity = any("source_identity_key = models.CharField(" in lines[i] for i in range(doc_idx, ver_idx))
if not has_identity:
    code_idx = next((i for i in range(doc_idx, ver_idx) if lines[i].startswith("    code = models.CharField(")), -1)
    if code_idx == -1:
        raise SystemExit("ERROR: no se encontró Document.code.")
    close_idx = next((i for i in range(code_idx + 1, ver_idx) if lines[i].strip() == ")"), -1)
    if close_idx == -1:
        raise SystemExit("ERROR: no se encontró cierre de Document.code.")
    field = [
        "\n",
        "    source_identity_key = models.CharField(\n",
        "        max_length=64,\n",
        "        null=True,\n",
        "        blank=True,\n",
        "        unique=True,\n",
        "        db_index=True,\n",
        "        help_text=(\n",
        '            "Huella estable de la identidad documental importada. "\n',
        '            "Permite reejecutar la promoción sin duplicar documentos."\n',
        "        ),\n",
        "    )\n",
    ]
    lines[close_idx + 1:close_idx + 1] = field

# Recalcular índices.
doc_idx = find_class("Document(")
ver_idx = find_class("DocumentVersion(")
evidence_idx = find_class("Evidence(")

# 3) Document.owner nullable + help_text
owner_idx = next((i for i in range(doc_idx, ver_idx) if lines[i].startswith("    owner = models.ForeignKey(")), -1)
if owner_idx == -1:
    raise SystemExit("ERROR: no se encontró Document.owner.")
owner_close = next((i for i in range(owner_idx + 1, ver_idx) if lines[i].strip() == ")"), -1)
if owner_close == -1:
    raise SystemExit("ERROR: no se encontró cierre de Document.owner.")
owner_text = "".join(lines[owner_idx:owner_close + 1])
if "null=True" not in owner_text:
    auth_idx = next((i for i in range(owner_idx + 1, owner_close) if "settings.AUTH_USER_MODEL" in lines[i]), -1)
    if auth_idx == -1:
        raise SystemExit("ERROR: no se encontró AUTH_USER_MODEL en owner.")
    lines[auth_idx + 1:auth_idx + 1] = ["        null=True,\n", "        blank=True,\n"]

# Recalcular cierre owner y añadir help_text si falta.
doc_idx = find_class("Document(")
ver_idx = find_class("DocumentVersion(")
owner_idx = next(i for i in range(doc_idx, ver_idx) if lines[i].startswith("    owner = models.ForeignKey("))
owner_close = next(i for i in range(owner_idx + 1, ver_idx) if lines[i].strip() == ")")
owner_text = "".join(lines[owner_idx:owner_close + 1])
if "Responsable documental. Puede quedar pendiente" not in owner_text:
    help_lines = [
        "        help_text=(\n",
        '            "Responsable documental. Puede quedar pendiente "\n',
        '            "durante una importación histórica."\n',
        "        ),\n",
    ]
    lines[owner_close:owner_close] = help_lines

# 4) Cambiar default del status de Document.
doc_idx = find_class("Document(")
ver_idx = find_class("DocumentVersion(")
status_idx = next((i for i in range(doc_idx, ver_idx) if lines[i].startswith("    status = models.CharField(")), -1)
if status_idx == -1:
    raise SystemExit("ERROR: no se encontró Document.status.")
status_close = next(i for i in range(status_idx + 1, ver_idx) if lines[i].strip() == ")")
for i in range(status_idx, status_close + 1):
    if "default=LifecycleStatus." in lines[i]:
        lines[i] = lines[i].replace("default=LifecycleStatus.DRAFT", "default=LifecycleStatus.UNKNOWN")

# 5) Cambiar default del status de DocumentVersion.
ver_idx = find_class("DocumentVersion(")
evidence_idx = find_class("Evidence(")
status_idx = next((i for i in range(ver_idx, evidence_idx) if lines[i].startswith("    status = models.CharField(")), -1)
if status_idx == -1:
    raise SystemExit("ERROR: no se encontró DocumentVersion.status.")
status_close = next(i for i in range(status_idx + 1, evidence_idx) if lines[i].strip() == ")")
for i in range(status_idx, status_close + 1):
    if "default=LifecycleStatus." in lines[i]:
        lines[i] = lines[i].replace("default=LifecycleStatus.DRAFT", "default=LifecycleStatus.UNKNOWN")

# 6) Importar modelos de promoción.
promotion_import = "from .models_promotion import DocumentImportIssue, DocumentVersionRepresentation\n"
if not any(line == promotion_import for line in lines):
    if lines and lines[-1].strip():
        lines.append("\n")
    lines.append(promotion_import)

path.write_text("".join(lines), encoding="utf-8")
print("OK: models.py actualizado con parche robusto V58B.")
print(f"Backup: {backup}")
print("- LifecycleStatus.UNKNOWN")
print("- Document.source_identity_key")
print("- Document.owner nullable")
print("- Document.status default UNKNOWN")
print("- DocumentVersion.status default UNKNOWN")
print("- modelos de promoción registrados")
