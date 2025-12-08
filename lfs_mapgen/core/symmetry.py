from __future__ import annotations
from .types import MapGrid


def mirror_vertical(grid: MapGrid) -> MapGrid:
    return [row[:] + row[::-1] for row in grid]

def mirror_horizontal(grid: MapGrid) -> MapGrid:
    return grid + grid[::-1]
