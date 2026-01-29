from __future__ import annotations

from typing import List, Tuple
import random

from .types import MapGrid
from .ca_walls import _in_bounds


Coord = Tuple[int, int]


def _is_floor(grid: MapGrid, x: int, y: int) -> bool:
    return grid[y][x] == "FL"


def _protected(x: int, y: int, centers: List[Coord], radius: int) -> bool:
    r2 = radius * radius
    for cx, cy in centers:
        dx = x - cx
        dy = y - cy
        if dx * dx + dy * dy <= r2:
            return True
    return False


def _collect_floor_cells(grid: MapGrid, protected_centers: List[Coord], protected_radius: int) -> List[Coord]:
    h = len(grid)
    w = len(grid[0]) if h else 0
    out: List[Coord] = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] != "FL":
                continue
            if _protected(x, y, protected_centers, protected_radius):
                continue
            out.append((x, y))
    return out


def _place_percent(
    grid: MapGrid,
    rng: random.Random,
    candidates: List[Coord],
    percent: float,
    tile: str,
) -> None:
    if percent <= 0.0 or not candidates:
        return

    n = int(len(candidates) * percent)
    if n <= 0:
        return

    rng.shuffle(candidates)
    for i in range(min(n, len(candidates))):
        x, y = candidates[i]
        if grid[y][x] == "FL":
            grid[y][x] = tile


def place_features_in_place(
    grid: MapGrid,
    rng: random.Random,
    water_percent: float,
    holes_percent: float,
    spikes_percent: float,
    protected_radius: int,
    protected_centers: List[Coord],
) -> None:
    candidates = _collect_floor_cells(grid, protected_centers, protected_radius)

    # Place in any order you like; this one avoids overwriting by re-collecting each time.
    _place_percent(grid, rng, candidates, water_percent, "WA")

    candidates = _collect_floor_cells(grid, protected_centers, protected_radius)
    _place_percent(grid, rng, candidates, holes_percent, "HO")

    candidates = _collect_floor_cells(grid, protected_centers, protected_radius)
    _place_percent(grid, rng, candidates, spikes_percent, "SP")
