from pathlib import Path

path = Path("apps/documents/models.py")
text = path.read_text(encoding="utf-8")

backup = Path("apps/documents/models_before_v58c.bak")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

lines = text.splitlines(keepends=True)


def find_class(prefix):
    for i, line in enumerate(lines):
        if line.lstrip().startswith(f"class {prefix}"):
            return i
    return -1


def find_next_class(start):
    for i in range(start + 1, len(lines)):
        if lines[i].lstrip().startswith("class "):
            return i
    return len(lines)


def find_field(class_start, class_end, field_name, constructor):
    target = f"{field_name} = models.{constructor}("
    for i in range(class_start, class_end):
        if lines[i].strip() == target:
            return i
    return -1


def field_close(start, class_end):
    for i in range(start + 1, class_end):
        if lines[i].strip() == ")":
            return i
    return -1


doc_idx = find_class("Document(")
ver_idx = find_class("DocumentVersion(")
evidence_idx = find_class("Evidence(")

if doc_idx == -1 or ver_idx == -1 or evidence_idx == -1:
    raise SystemExit(
        "ERROR: no se localizaron Document, DocumentVersion y Evidence."
    )

# 1) Document.source_identity_key
doc_end = ver_idx
identity_exists = any(
    "source_identity_key = models.CharField(" in lines[i]
    for i in range(doc_idx, doc_end)
)

if not identity_exists:
    code_idx = find_field(doc_idx, doc_end, "code", "CharField")
    if code_idx == -1:
        raise SystemExit("ERROR: no se encontró Document.code.")
    close = field_close(code_idx, doc_end)
    if close == -1:
        raise SystemExit("ERROR: no se encontró cierre de Document.code.")

    identity_lines = [
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
    lines[close + 1:close + 1] = identity_lines

# Recalcular índices después de insertar.
doc_idx = find_class("Document(")
ver_idx = find_class("DocumentVersion(")
evidence_idx = find_class("Evidence(")
doc_end = ver_idx

# 2) Document.owner nullable
owner_idx = find_field(doc_idx, doc_end, "owner", "ForeignKey")
if owner_idx == -1:
    raise SystemExit("ERROR: no se encontró Document.owner.")

owner_close = field_close(owner_idx, doc_end)
if owner_close == -1:
    raise SystemExit("ERROR: no se encontró cierre de Document.owner.")

owner_text = "".join(lines[owner_idx:owner_close + 1])

if "null=True" not in owner_text:
    auth_idx = next(
        (
            i for i in range(owner_idx + 1, owner_close)
            if "settings.AUTH_USER_MODEL" in lines[i]
        ),
        -1,
    )
    if auth_idx == -1:
        raise SystemExit("ERROR: no se encontró AUTH_USER_MODEL en owner.")
    lines[auth_idx + 1:auth_idx + 1] = [
        "        null=True,\n",
        "        blank=True,\n",
    ]

# Recalcular bloque owner.
doc_idx = find_class("Document(")
ver_idx = find_class("DocumentVersion(")
owner_idx = find_field(doc_idx, ver_idx, "owner", "ForeignKey")
owner_close = field_close(owner_idx, ver_idx)
owner_text = "".join(lines[owner_idx:owner_close + 1])

if "Responsable documental. Puede quedar pendiente" not in owner_text:
    lines[owner_close:owner_close] = [
        "        help_text=(\n",
        '            "Responsable documental. Puede quedar pendiente "\n',
        '            "durante una importación histórica."\n',
        "        ),\n",
    ]

# 3) Document.status nullable para estado no determinado.
doc_idx = find_class("Document(")
ver_idx = find_class("DocumentVersion(")
status_idx = find_field(doc_idx, ver_idx, "status", "CharField")
if status_idx == -1:
    raise SystemExit("ERROR: no se encontró Document.status.")
status_close = field_close(status_idx, ver_idx)

status_text = "".join(lines[status_idx:status_close + 1])
insertions = []
if "null=True" not in status_text:
    insertions.append("        null=True,\n")
if "blank=True" not in status_text:
    insertions.append("        blank=True,\n")

# Reemplazar default existente por None.
for i in range(status_idx, status_close + 1):
    if "default=LifecycleStatus." in lines[i]:
        lines[i] = "        default=None,\n"

if insertions:
    # Insertar después de max_length.
    max_idx = next(
        (
            i for i in range(status_idx + 1, status_close)
            if "max_length=" in lines[i]
        ),
        status_idx,
    )
    lines[max_idx + 1:max_idx + 1] = insertions

# 4) DocumentVersion.status nullable.
ver_idx = find_class("DocumentVersion(")
evidence_idx = find_class("Evidence(")
status_idx = find_field(ver_idx, evidence_idx, "status", "CharField")
if status_idx == -1:
    raise SystemExit("ERROR: no se encontró DocumentVersion.status.")
status_close = field_close(status_idx, evidence_idx)
status_text = "".join(lines[status_idx:status_close + 1])

insertions = []
if "null=True" not in status_text:
    insertions.append("        null=True,\n")
if "blank=True" not in status_text:
    insertions.append("        blank=True,\n")

for i in range(status_idx, status_close + 1):
    if "default=LifecycleStatus." in lines[i]:
        lines[i] = "        default=None,\n"

if insertions:
    max_idx = next(
        (
            i for i in range(status_idx + 1, status_close)
            if "max_length=" in lines[i]
        ),
        status_idx,
    )
    lines[max_idx + 1:max_idx + 1] = insertions

# 5) Registrar modelos de promoción.
promotion_import = (
    "from .models_promotion import "
    "DocumentImportIssue, DocumentVersionRepresentation\n"
)

if promotion_import not in lines:
    if lines and lines[-1].strip():
        lines.append("\n")
    lines.append(promotion_import)

path.write_text("".join(lines), encoding="utf-8")

print("OK: models.py actualizado con V58C.")
print(f"Backup: {backup}")
print("- Document.source_identity_key agregado/verificado")
print("- Document.owner ahora admite NULL")
print("- Document.status usa NULL para estado no determinado")
print("- DocumentVersion.status usa NULL para estado no determinado")
print("- DocumentImportIssue registrado")
print("- DocumentVersionRepresentation registrado")
