from __future__ import annotations

from dataclasses import dataclass
from heapq import heappush, heappop
from typing import Dict, List, Optional, Tuple
import random

from .types import MapGrid
from .ca_walls import carve_disk, _in_bounds


Coord = Tuple[int, int]

def _neighbors8(x: int, y: int) -> List[Coord]:
    return [
        (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
        (x - 1, y),                 (x + 1, y),
        (x - 1, y + 1), (x, y + 1), (x + 1, y + 1),
    ]


def _flood_component(grid: MapGrid, start: Coord, visited: set[Coord]) -> List[Coord]:
    h = len(grid)
    w = len(grid[0]) if h else 0

    stack = [start]
    visited.add(start)
    comp: List[Coord] = []

    while stack:
        x, y = stack.pop()
        comp.append((x, y))
        for nx, ny in _neighbors4(x, y):
            if not _in_bounds(nx, ny, w, h):
                continue
            if (nx, ny) in visited:
                continue
            if grid[ny][nx] != "FL":
                continue
            visited.add((nx, ny))
            stack.append((nx, ny))

    return comp


def _find_floor_components(grid: MapGrid) -> List[List[Coord]]:
    h = len(grid)
    w = len(grid[0]) if h else 0

    visited: set[Coord] = set()
    comps: List[List[Coord]] = []

    for y in range(h):
        for x in range(w):
            if grid[y][x] != "FL":
                continue
            if (x, y) in visited:
                continue
            comps.append(_flood_component(grid, (x, y), visited))

    return comps


def _component_index_of_cell(comps: List[List[Coord]], cell: Coord) -> int | None:
    cx, cy = cell
    for i, comp in enumerate(comps):
        # comps are usually not huge; linear scan is fine for these map sizes
        for x, y in comp:
            if x == cx and y == cy:
                return i
    return None


def _neighbors4(x: int, y: int) -> List[Coord]:
    return [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]


def _tile_cost(t: str) -> int:
    # Carving through walls is allowed but "costly", so A* prefers existing floors.
    if t == "FL":
        return 0
    if t == "WL":
        return 6
    if t == "IW":
        return 10_000_000
    # Features shouldn't exist yet, but just in case:
    return 2


def _heur(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _a_star(grid: MapGrid, start: Coord, goal: Coord) -> Optional[List[Coord]]:
    h = len(grid)
    w = len(grid[0]) if h else 0

    open_heap: List[Tuple[int, int, Coord]] = []
    heappush(open_heap, (0, 0, start))

    came_from: Dict[Coord, Coord] = {}
    gscore: Dict[Coord, int] = {start: 0}

    counter = 0

    while open_heap:
        _, _, cur = heappop(open_heap)
        if cur == goal:
            # reconstruct
            path = [cur]
            while cur in came_from:
                cur = came_from[cur]
                path.append(cur)
            path.reverse()
            return path

        cx, cy = cur
        for nx, ny in _neighbors4(cx, cy):
            if not _in_bounds(nx, ny, w, h):
                continue
            if grid[ny][nx] == "IW":
                continue

            tentative = gscore[cur] + _tile_cost(grid[ny][nx])
            ncoord = (nx, ny)
            if tentative < gscore.get(ncoord, 1_000_000_000):
                came_from[ncoord] = cur
                gscore[ncoord] = tentative
                counter += 1
                f = tentative + _heur(ncoord, goal)
                heappush(open_heap, (f, counter, ncoord))

    return None


def _carve_path(grid: MapGrid, path: List[Coord], radius: int) -> None:
    for x, y in path:
        carve_disk(grid, x, y, radius, tile="FL")


def connect_spawns_in_place(
    grid: MapGrid,
    spawns: List[Coord],
    rng: random.Random,
    corridor_radius: int = 1,
    protected_radius: int = 3,
    extra_corridors: int = 0,
    extra_corridor_radius: int | None = None,
) -> None:
    if not spawns:
        return

    root = spawns[0]

    for sx, sy in spawns:
        carve_disk(grid, sx, sy, protected_radius, tile="FL")

    # Primary: connect spawns to root
    for target in spawns[1:]:
        path = _a_star(grid, root, target)
        if not path:
            path = _fallback_path(root, target, rng)
        _carve_path(grid, path, corridor_radius)
        carve_disk(grid, root[0], root[1], protected_radius, tile="FL")
        carve_disk(grid, target[0], target[1], protected_radius, tile="FL")

    # Extra: carve additional corridors between random floor points
    if extra_corridors > 0:
        floors = _all_floor_cells(grid)
        if len(floors) >= 2:
            r = corridor_radius if extra_corridor_radius is None else extra_corridor_radius
            for _ in range(extra_corridors):
                a = rng.choice(floors)
                b = rng.choice(floors)
                if a == b:
                    continue
                path = _a_star(grid, a, b)
                if path:
                    _carve_path(grid, path, r)

def connect_all_floor_regions_in_place(
    grid: MapGrid,
    spawns: List[Coord],
    rng: random.Random,
    corridor_radius: int = 1,
    protected_radius: int = 3,
) -> None:
    # Ensure spawn disks are floor
    for sx, sy in spawns:
        carve_disk(grid, sx, sy, protected_radius, tile="FL")

    while True:
        comps = _find_floor_components(grid)
        if len(comps) <= 1:
            return

        # Pick main component: the one containing first spawn if possible, else largest
        main_idx: int | None = None
        if spawns:
            si = _component_index_of_cell(comps, spawns[0])
            if si is not None:
                main_idx = si

        if main_idx is None:
            main_idx = max(range(len(comps)), key=lambda i: len(comps[i]))

        main = comps[main_idx]

        # Find a component to connect (pick the one with nearest pair to main, cheap heuristic)
        best_pair: tuple[Coord, Coord] | None = None
        best_dist = 1_000_000_000

        # Sample a few points to keep it fast on big maps
        main_samples = main if len(main) <= 400 else [main[i] for i in range(0, len(main), max(1, len(main) // 400))]

        for i, comp in enumerate(comps):
            if i == main_idx:
                continue

            comp_samples = comp if len(comp) <= 200 else [comp[j] for j in range(0, len(comp), max(1, len(comp) // 200))]

            for a in main_samples:
                ax, ay = a
                for b in comp_samples:
                    bx, by = b
                    d = abs(ax - bx) + abs(ay - by)
                    if d < best_dist:
                        best_dist = d
                        best_pair = (a, b)

        if not best_pair:
            return

        a, b = best_pair
        path = _a_star(grid, a, b)
        if not path:
            path = _fallback_path(a, b, rng)

        _carve_path(grid, path, corridor_radius)

        # Keep spawns clear
        for sx, sy in spawns:
            carve_disk(grid, sx, sy, protected_radius, tile="FL")


def _fallback_path(a: Coord, b: Coord, rng: random.Random) -> List[Coord]:
    ax, ay = a
    bx, by = b
    path: List[Coord] = [(ax, ay)]

    x, y = ax, ay
    while (x, y) != (bx, by):
        dx = 0 if x == bx else (1 if bx > x else -1)
        dy = 0 if y == by else (1 if by > y else -1)

        # randomize whether we step in x or y when both are possible
        if dx != 0 and dy != 0:
            if rng.random() < 0.5:
                x += dx
            else:
                y += dy
        elif dx != 0:
            x += dx
        else:
            y += dy

        path.append((x, y))

    return path

def convert_hidden_walls_to_indestructible_in_place(grid: MapGrid) -> None:
    h = len(grid)
    w = len(grid[0]) if h else 0

    def touches_floor(x: int, y: int) -> bool:
        for nx, ny in _neighbors8(x, y):
            if not _in_bounds(nx, ny, w, h):
                continue
            if grid[ny][nx] == "FL":
                return True
        return False

    for y in range(h):
        for x in range(w):
            if grid[y][x] != "WL":
                continue
            # If this wall does not touch any floor, it is "inside rock" => make it IW
            if not touches_floor(x, y):
                grid[y][x] = "IW"


def _all_floor_cells(grid: MapGrid) -> List[Coord]:
    h = len(grid)
    w = len(grid[0]) if h else 0
    out: List[Coord] = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] == "FL":
                out.append((x, y))
    return out
