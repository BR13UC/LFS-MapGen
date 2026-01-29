from __future__ import annotations

from typing import List, Tuple
import random

from .types import MapGrid


def mirror_spawns_vertical(spawns: List[Tuple[int, int]], width: int) -> List[Tuple[int, int]]:
    return [((width - 1) - x, y) for x, y in spawns]


def _in_bounds(x: int, y: int, w: int, h: int) -> bool:
    return 0 <= x < w and 0 <= y < h


def carve_disk(grid: MapGrid, cx: int, cy: int, r: int, tile: str = "FL") -> None:
    h = len(grid)
    w = len(grid[0]) if h else 0
    r2 = r * r
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if not _in_bounds(x, y, w, h):
                continue
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                if grid[y][x] != "IW":
                    grid[y][x] = tile


def _count_wall_neighbors_8(grid: MapGrid, x: int, y: int) -> int:
    h = len(grid)
    w = len(grid[0]) if h else 0
    c = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if not _in_bounds(nx, ny, w, h):
                c += 1  # out-of-bounds behaves like wall
            elif grid[ny][nx] in ("IW", "WL"):
                c += 1
    return c


def _ca_step(grid: MapGrid, birth_limit: int, death_limit: int) -> MapGrid:
    h = len(grid)
    w = len(grid[0]) if h else 0
    out: MapGrid = [[grid[y][x] for x in range(w)] for y in range(h)]

    for y in range(h):
        for x in range(w):
            if grid[y][x] == "IW":
                continue

            n = _count_wall_neighbors_8(grid, x, y)

            if grid[y][x] == "WL":
                # wall survives if it has enough wall neighbors
                out[y][x] = "WL" if n >= death_limit else "FL"
            else:
                # floor becomes wall if surrounded
                out[y][x] = "WL" if n >= birth_limit else "FL"

    return out


def generate_ca_walls_grid(
    width: int,
    height: int,
    rng: random.Random,
    initial_wall_prob: float = 0.45,
    passes: int = 5,
    birth_limit: int = 5,
    death_limit: int = 3,
) -> MapGrid:
    # 1) random init
    grid: MapGrid = [["WL" if rng.random() < initial_wall_prob else "FL" for _ in range(width)] for _ in range(height)]

    # 2) borders are IW
    for x in range(width):
        grid[0][x] = "IW"
        grid[height - 1][x] = "IW"
    for y in range(height):
        grid[y][0] = "IW"
        grid[y][width - 1] = "IW"

    # 3) CA passes
    for _ in range(max(0, passes)):
        grid = _ca_step(grid, birth_limit=birth_limit, death_limit=death_limit)

        # keep border IW
        for x in range(width):
            grid[0][x] = "IW"
            grid[height - 1][x] = "IW"
        for y in range(height):
            grid[y][0] = "IW"
            grid[y][width - 1] = "IW"

    return grid
