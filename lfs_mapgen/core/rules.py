from __future__ import annotations
from .types import MapGrid


def ensure_connectivity(grid: MapGrid) -> MapGrid:
    # Old behavior removed: connectivity is now handled by connectivity.py (corridor carving).
    return grid
