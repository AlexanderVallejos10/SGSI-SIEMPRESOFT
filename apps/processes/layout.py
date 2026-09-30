"""Ubicación de procesos dentro de su franja del mapa."""

from .models import LANE_KINDS, ProcessNode

NODE_W, NODE_H = 180, 56
COLUMNS = (40, 255, 470, 685, 900)
FIRST_ROW, ROW_STEP = 40, 90


def _overlaps(x, y, others):
    return any(abs(x - ox) < NODE_W + 20 and abs(y - oy) < NODE_H + 20 for ox, oy in others)


def free_slot(category, exclude_pk=None):
    """Primer lugar libre de la franja, recorriendo filas de izquierda a derecha."""
    if category.kind not in LANE_KINDS:
        return 0, 0
    others = [
        (p.x, p.y)
        for p in ProcessNode.objects.filter(category=category, is_active=True).exclude(pk=exclude_pk)
    ]
    for row in range(7):
        y = FIRST_ROW + row * ROW_STEP
        for x in COLUMNS:
            if not _overlaps(x, y, others):
                return x, y
    return COLUMNS[0], FIRST_ROW + 7 * ROW_STEP
