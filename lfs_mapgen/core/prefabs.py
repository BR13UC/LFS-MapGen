from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Literal, Optional, Sequence, Tuple
import json
import os
import random

from .types import MapGrid

Category = Literal["STRUCTURE", "FEATURE"]
Token = str


@dataclass(frozen=True)
class PrefabPatch:
    x: int
    y: int
    tile: str


@dataclass(frozen=True)
class Prefab:
    id: str
    category: Category
    size: Tuple[int, int]
    reserve: Tuple[int, int]
    probability: float
    before: List[List[Token]]
    after: List[PrefabPatch]


# ----------------------------- loading -----------------------------

def load_prefabs_from_json(path: str) -> List[Prefab]:
    """
    Loads prefabs from a JSON file in the format:
    {
        "prefabs": [
            { "id": ..., "category": ..., "size": [w,h], "reserve": [rw,rh],
              "probability": 0.xx, "before": [[...]], "after": [{"x":..,"y":..,"tile":"..."}]
            }
        ]
    }
    """
    if not path:
        return []

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Prefab JSON not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_prefabs = data.get("prefabs")
    if not isinstance(raw_prefabs, list):
        raise ValueError("Prefab JSON must contain a top-level 'prefabs' list.")

    result: List[Prefab] = []
    for item in raw_prefabs:
        if not isinstance(item, dict):
            continue

        prefab_id = str(item["id"])
        category = item["category"]
        if category not in ("STRUCTURE", "FEATURE"):
            raise ValueError(f"Invalid prefab category for '{prefab_id}': {category}")

        size = item["size"]
        reserve = item.get("reserve", size)
        probability = float(item.get("probability", 1.0))
        before = item["before"]
        after = item.get("after", [])

        if (
            not isinstance(size, list) or len(size) != 2
            or not isinstance(reserve, list) or len(reserve) != 2
        ):
            raise ValueError(f"Invalid size/reserve for '{prefab_id}'.")

        w, h = int(size[0]), int(size[1])
        rw, rh = int(reserve[0]), int(reserve[1])

        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid prefab size for '{prefab_id}': {size}")
        if rw < w or rh < h:
            raise ValueError(f"Reserve must be >= size for '{prefab_id}'.")

        if not isinstance(before, list) or len(before) != h:
            raise ValueError(f"'before' height mismatch for '{prefab_id}'.")
        for row in before:
            if not isinstance(row, list) or len(row) != w:
                raise ValueError(f"'before' width mismatch for '{prefab_id}'.")

        patches: List[PrefabPatch] = []
        for p in after:
            if not isinstance(p, dict):
                continue
            patches.append(
                PrefabPatch(
                    x=int(p["x"]),
                    y=int(p["y"]),
                    tile=str(p["tile"]),
                )
            )

        result.append(
            Prefab(
                id=prefab_id,
                category=category,
                size=(w, h),
                reserve=(rw, rh),
                probability=probability,
                before=before,
                after=patches,
            )
        )

    return result


# ----------------------------- tile helpers -----------------------------

def _is_solid(tile: str) -> bool:
    return tile in ("WL", "IW")


def _token_matches(tile: str, token: Token) -> bool:
    if token == "ANY":
        return True
    if token == "SOLID":
        return _is_solid(tile)
    if token.startswith("MT:"):
        mt = token.split(":", 1)[1]
        if mt == "FLOOR":
            return tile == "FL"
        if mt == "WALL":
            return tile == "WL"
        if mt == "IW":
            return tile == "IW"
        return False
    return False


def _logical_to_tile_id(logical: str) -> Optional[str]:
    mapping = {
        "FLOOR": "FL",
        "WALL_BREAKABLE": "WL",
        "WALL_INBREAKABLE": "IW",
        "SPIKE": "SP",
        "WATER": "WA",
        "HOLE": "HO",
    }
    return mapping.get(logical)


def _rotate_grid_cw(before: List[List[Token]]) -> List[List[Token]]:
    # before is h rows of w tokens
    h = len(before)
    w = len(before[0]) if h else 0
    # result is w rows of h tokens
    return [[before[h - 1 - y][x] for y in range(h)] for x in range(w)]


def _rotate_patch_cw(patch: PrefabPatch, w: int, h: int) -> PrefabPatch:
    # 90° clockwise: (x, y) -> (h-1-y, x)
    return PrefabPatch(x=h - 1 - patch.y, y=patch.x, tile=patch.tile)


def _rotate_prefab_cw(prefab: Prefab) -> Prefab:
    w, h = prefab.size
    rw, rh = prefab.reserve

    new_before = _rotate_grid_cw(prefab.before)
    new_patches = [_rotate_patch_cw(p, w, h) for p in prefab.after]

    # size swaps, reserve swaps
    return Prefab(
        id=prefab.id,
        category=prefab.category,
        size=(h, w),
        reserve=(rh, rw),
        probability=prefab.probability,
        before=new_before,
        after=new_patches,
    )


def expand_prefabs_with_rotations(prefabs: Sequence[Prefab]) -> List[Prefab]:
    """
    For each prefab, generate 0/90/180/270 variants in-memory.
    Keeps JSON unchanged.
    """
    expanded: List[Prefab] = []
    for p in prefabs:
        r0 = p
        r1 = _rotate_prefab_cw(r0)
        r2 = _rotate_prefab_cw(r1)
        r3 = _rotate_prefab_cw(r2)

        # Deduplicate identical variants (e.g. square symmetric patterns)
        uniq: List[Prefab] = []
        seen = set()
        for r in (r0, r1, r2, r3):
            key = (
                r.size,
                r.reserve,
                tuple(tuple(row) for row in r.before),
                tuple((pp.x, pp.y, pp.tile) for pp in r.after),
                r.category,
                r.probability,
            )
            if key in seen:
                continue
            seen.add(key)
            uniq.append(r)

        expanded.extend(uniq)
    return expanded


# ----------------------------- reservations -----------------------------

def _rects_overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1)


def _in_bounds_rect(x1: int, y1: int, x2: int, y2: int, w: int, h: int) -> bool:
    return 0 <= x1 < w and 0 <= y1 < h and 0 <= x2 < w and 0 <= y2 < h


def _compute_reserve_rect(
    x: int,
    y: int,
    pw: int,
    ph: int,
    rw: int,
    rh: int,
) -> Tuple[int, int, int, int]:
    pad_x = max(0, (rw - pw) // 2)
    pad_y = max(0, (rh - ph) // 2)
    rx1 = x - pad_x
    ry1 = y - pad_y
    rx2 = x + pw - 1 + pad_x
    ry2 = y + ph - 1 + pad_y
    return rx1, ry1, rx2, ry2


def _protected_cell(x: int, y: int, centers: Sequence[Tuple[int, int]], radius: int) -> bool:
    r2 = radius * radius
    for cx, cy in centers:
        dx = x - cx
        dy = y - cy
        if dx * dx + dy * dy <= r2:
            return True
    return False


# ----------------------------- core pass -----------------------------

def apply_prefab_pass_in_place(
    grid: MapGrid,
    rng: random.Random,
    prefabs: Sequence[Prefab],
    category: Category,
    protected_centers: Sequence[Tuple[int, int]] = (),
    protected_radius: int = 0,
    on_apply: Optional[Callable[[int], None]] = None,
) -> int:
    prefabs = expand_prefabs_with_rotations(prefabs)
    h = len(grid)
    w = len(grid[0]) if h else 0
    if w == 0 or h == 0:
        return 0

    pools: Dict[Tuple[int, int], List[Prefab]] = {}
    for p in prefabs:
        if p.category != category:
            continue
        pools.setdefault(p.size, []).append(p)

    sizes = sorted(pools.keys(), key=lambda s: (s[0] * s[1], s[0], s[1]), reverse=True)

    reserved_rects: List[Tuple[int, int, int, int]] = []
    applied = 0

    for y in range(h):
        for x in range(w):
            for (pw, ph) in sizes:
                if x + pw > w or y + ph > h:
                    continue

                if protected_radius > 0 and _protected_cell(x, y, protected_centers, protected_radius):
                    continue

                matches: List[Prefab] = []
                for prefab in pools[(pw, ph)]:
                    rw, rh = prefab.reserve
                    rx1, ry1, rx2, ry2 = _compute_reserve_rect(x, y, pw, ph, rw, rh)

                    if not _in_bounds_rect(rx1, ry1, rx2, ry2, w, h):
                        continue

                    if protected_radius > 0:
                        blocked = False
                        for yy in range(ry1, ry2 + 1):
                            for xx in range(rx1, rx2 + 1):
                                if _protected_cell(xx, yy, protected_centers, protected_radius):
                                    blocked = True
                                    break
                            if blocked:
                                break
                        if blocked:
                            continue

                    overlap = False
                    for r in reserved_rects:
                        if _rects_overlap((rx1, ry1, rx2, ry2), r):
                            overlap = True
                            break
                    if overlap:
                        continue

                    ok = True
                    for dy in range(ph):
                        row = prefab.before[dy]
                        for dx in range(pw):
                            if not _token_matches(grid[y + dy][x + dx], row[dx]):
                                ok = False
                                break
                        if not ok:
                            break
                    if not ok:
                        continue

                    matches.append(prefab)

                if not matches:
                    continue

                chosen = rng.choice(matches)
                if chosen.probability < 1.0 and rng.random() > chosen.probability:
                    continue

                for patch in chosen.after:
                    tx = x + patch.x
                    ty = y + patch.y
                    tile_id = _logical_to_tile_id(patch.tile)
                    if tile_id is None:
                        continue
                    if grid[ty][tx] == "IW" and tile_id != "IW":
                        continue
                    grid[ty][tx] = tile_id

                rw, rh = chosen.reserve
                rx1, ry1, rx2, ry2 = _compute_reserve_rect(x, y, pw, ph, rw, rh)
                reserved_rects.append((rx1, ry1, rx2, ry2))

                applied += 1
                if on_apply is not None:
                    on_apply(applied)
                break

    return applied
