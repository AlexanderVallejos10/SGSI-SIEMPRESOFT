from django.contrib.staticfiles import finders

RIVE_MOTOR = ("vendor/rive/rive.js", "vendor/rive/rive.wasm")
RIVE_ESCUDO = "rive/sgsi_escudo.riv"


def rive_disponible():
    return all(finders.find(ruta) for ruta in (*RIVE_MOTOR, RIVE_ESCUDO))
