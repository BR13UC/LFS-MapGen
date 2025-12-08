from __future__ import annotations
from collections import deque
from typing import List, Tuple
from .tiles import TileId
from .types import MapGrid


def is_floor(tile: TileId) -> bool:
    return tile == "FL"

def ensure_connectivity(grid: MapGrid) -> MapGrid:
    h = len(grid)
    w = len(grid[0]) if h else 0
    visited = [[False] * w for _ in range(h)]

    start = None
    for y in range(h):
        for x in range(w):
            if is_floor(grid[y][x]):
                start = (x, y)
                break
        if start:
            break

    if not start:
        return grid

    q = deque([start])
    visited[start[1]][start[0]] = True

    while q:
        x, y = q.popleft()
        for nx, ny in neighbors(x, y, w, h):
            if not visited[ny][nx] and is_floor(grid[ny][nx]):
                visited[ny][nx] = True
                q.append((nx, ny))

    for y in range(h):
        for x in range(w):
            if grid[y][x] == "FL" and not visited[y][x]:
                grid[y][x] = "WL"

    return grid

def neighbors(x: int, y: int, w: int, h: int):
    if x > 0: yield (x - 1, y)
    if x < w - 1: yield (x + 1, y)
    if y > 0: yield (x, y - 1)
    if y < h - 1: yield (x, y + 1)
