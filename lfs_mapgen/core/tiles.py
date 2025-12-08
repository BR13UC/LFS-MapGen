from __future__ import annotations
from typing import Dict, Tuple

TileId = str


VALID_TILES: Dict[TileId, str] = {
    "IW": "Inbreakable Wall",
    "WL": "Wall",
    "FL": "Floor",
    "WA": "Water",
    "HO": "Hole",
    "SP": "Spikes",
}

TILE_COLORS: Dict[TileId, Tuple[int, int, int]] = {
    "IW": (40, 40, 40),
    "WL": (90, 90, 90),
    "FL": (200, 200, 200),
    "WA": (0, 120, 255),
    "HO": (30, 30, 30),
    "SP": (255, 60, 60),
}

PALETTE_TILES = list(VALID_TILES.keys())
