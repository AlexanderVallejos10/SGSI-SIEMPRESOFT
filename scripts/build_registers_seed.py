"""Arma apps/registers/data/registros_siempresoft.json con las filas de los 29 registros, leídas de los
archivos reales de SiempreSoft con los mismos lectores que usa el sistema al importar.

Uso: python scripts/build_registers_seed.py <mapa.json> <salida.json>
     mapa.json = {"slug-del-registro": "ruta del archivo", ...}
"""

import importlib.util
import json
import sys
import types
import warnings

warnings.filterwarnings("ignore")
sys.dont_write_bytecode = True
pkg = types.ModuleType("apps.registers")
pkg.__path__ = ["apps/registers"]
sys.modules.setdefault("apps", types.ModuleType("apps"))
sys.modules["apps.registers"] = pkg
for name in ("schemas", "importers"):
    spec = importlib.util.spec_from_file_location(f"apps.registers.{name}", f"apps/registers/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
schemas = sys.modules["apps.registers.schemas"]
importers = sys.modules["apps.registers.importers"]


def main(map_path, out_path):
    sources = json.load(open(map_path, encoding="utf-8"))
    out = {}
    for slug, entry in sources.items():
        path, default_year = (entry, None) if isinstance(entry, str) else (entry["path"], entry.get("year"))
        schema = schemas.get(slug)
        with open(path, "rb") as fh:
            rows = importers.read(slug, fh, path)
        items = []
        for section, data in rows:
            data = dict(data)
            year = data.pop("_year", None)
            if schema["by_year"]:
                year = year or default_year or importers.year_from_name(path)
            items.append({"year": year if schema["by_year"] else None, "section": section, "data": data})
        out[slug] = {"source": path.rsplit("/", 1)[-1], "rows": items}
        print(f"{slug:26s} {len(items):5d}")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
