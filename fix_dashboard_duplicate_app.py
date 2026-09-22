from pathlib import Path
import re

path = Path("config/settings/base.py")
text = path.read_text(encoding="utf-8")

backup = Path("config/settings/base_before_dashboard_dedupe.bak")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

lines = text.splitlines(keepends=True)

dashboard_pattern = re.compile(
    r"""^\s*["']apps\.dashboard(?:\.apps\.DashboardConfig)?["']\s*,?\s*$"""
)

dashboard_indexes = [
    i for i, line in enumerate(lines)
    if dashboard_pattern.match(line)
]

if not dashboard_indexes:
    raise SystemExit(
        "ERROR: no se encontró ninguna entrada de apps.dashboard "
        "en config/settings/base.py"
    )

if len(dashboard_indexes) == 1:
    print("OK: solo existe una entrada de dashboard; no se modificó base.py.")
    print("Entrada:", lines[dashboard_indexes[0]].strip())
    raise SystemExit(0)

# Preferir la forma explícita DashboardConfig.
explicit_indexes = [
    i for i in dashboard_indexes
    if "apps.dashboard.apps.DashboardConfig" in lines[i]
]

keep_index = (
    explicit_indexes[0]
    if explicit_indexes
    else dashboard_indexes[0]
)

new_lines = []
removed = []

for i, line in enumerate(lines):
    if i in dashboard_indexes and i != keep_index:
        removed.append(line.strip())
        continue
    new_lines.append(line)

path.write_text("".join(new_lines), encoding="utf-8")

print("OK: INSTALLED_APPS depurado.")
print("Conservada:", lines[keep_index].strip())
print("Eliminadas:")
for item in removed:
    print(" -", item)
print("Backup:", backup)
