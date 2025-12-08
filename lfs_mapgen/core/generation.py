from __future__ import annotations
import random
from typing import List
from .tiles import TileId, PALETTE_TILES
from .types import MapData, MapGrid, SpawnDict
from .config import GenerationParams
from .rules import ensure_connectivity


class MapGenerator:
    def __init__(self, params: GenerationParams):
        self.params = params
        self.random = random.Random(params.seed)

    def generate(self) -> MapData:
        grid = self._generate_random_layer()
        spawns = self._generate_spawns()

        if self.params.enforce_connected_floor:
            grid = ensure_connectivity(grid)

        return MapData(grid=grid, spawns=spawns)

    def _generate_random_layer(self) -> MapGrid:
        w, h = self.params.width, self.params.height
        grid = [["FL" for _ in range(w)] for _ in range(h)]

        weights: List[TileId] = self._make_weight_list()
        for y in range(h):
            for x in range(w):
                grid[y][x] = self.random.choice(weights)

        return grid

    def _make_weight_list(self) -> List[TileId]:
        p = self.params
        weights = (
            ["FL"] * int(p.floor_percent * 100) +
            ["IW"] * int(p.wall_percent * 100) +
            ["WL"] * int(p.breakable_wall_percent * 100) +
            ["WA"] * int(p.water_percent * 100) +
            ["HO"] * int(p.holes_percent * 100) +
            ["SP"] * int(p.spikes_percent * 100)
        )
        return weights if weights else ["FL"]

    def _generate_spawns(self) -> SpawnDict:
        teams = {
            "team1": [],
            "team2": []
        }
        return teams
