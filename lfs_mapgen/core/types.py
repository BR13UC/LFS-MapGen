from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
from .tiles import TileId

MapGrid = List[List[TileId]]
SpawnDict = Dict[str, List[Tuple[int, int]]]


@dataclass
class MapData:
    grid: MapGrid
    spawns: SpawnDict
