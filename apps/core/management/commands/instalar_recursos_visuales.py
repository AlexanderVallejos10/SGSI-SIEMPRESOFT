"""Descarga una sola vez las librerías de animación y las deja dentro del sistema (static/vendor/).

    python manage.py instalar_recursos_visuales

- GSAP 3.13 (gratuito, incluidos sus complementos) con SplitText y DrawSVG: animación de la pantalla de ingreso.
- Lottie 5.12.2 (versión ligera): animación oficial del isotipo de SiempreSoft.

Versiones fijas. La huella SHA-256 de cada archivo queda en static/vendor/recursos.json; si alguien altera
un archivo, el comando lo detecta la próxima vez. Después de descargarlas el sistema funciona sin internet."""

import hashlib
import json
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

CDN = "https://cdnjs.cloudflare.com/ajax/libs"
FILES = {
    "vendor/gsap/gsap.min.js": f"{CDN}/gsap/3.13.0/gsap.min.js",
    "vendor/gsap/SplitText.min.js": f"{CDN}/gsap/3.13.0/SplitText.min.js",
    "vendor/gsap/DrawSVGPlugin.min.js": f"{CDN}/gsap/3.13.0/DrawSVGPlugin.min.js",
    "vendor/lottie_light.min.js": f"{CDN}/lottie-web/5.12.2/lottie_light.min.js",
}


class Command(BaseCommand):
    help = "Descarga GSAP y Lottie en static/vendor/ (una sola vez)."

    def add_arguments(self, parser):
        parser.add_argument("--forzar", action="store_true", help="Vuelve a descargar aunque ya existan.")

    def handle(self, *args, **opts):
        static = Path(settings.BASE_DIR) / "static"
        registry_path = static / "vendor" / "recursos.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}
        for rel, url in FILES.items():
            target = static / rel
            if target.exists() and not opts["forzar"]:
                digest = hashlib.sha256(target.read_bytes()).hexdigest()
                if registry.get(rel, {}).get("sha256") not in (None, digest):
                    raise CommandError(f"{rel} fue modificado (la huella no coincide). Use --forzar para reinstalarlo.")
                self.stdout.write(f"  {rel}: ya instalado")
                continue
            try:
                with urllib.request.urlopen(url, timeout=30) as response:
                    data = response.read()
            except Exception as exc:
                raise CommandError(f"No se pudo descargar {url}: {exc}")
            if len(data) < 2000 or b"<html" in data[:500].lower():
                raise CommandError(f"La descarga de {url} no parece un archivo JavaScript válido.")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            registry[rel] = {"url": url, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            self.stdout.write(self.style.SUCCESS(f"  {rel}: descargado ({len(data) // 1024} KB)"))
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS("Recursos visuales listos. Recargue la página con Ctrl + F5."))
