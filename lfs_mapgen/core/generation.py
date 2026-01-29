from __future__ import annotations

import random
from typing import Callable, List, Optional, Set, Tuple

from .config import GenerationParams
from .types import MapData, MapGrid, SpawnDict
from .ca_walls import generate_ca_walls_grid, mirror_spawns_vertical, carve_disk
from .connectivity import connect_spawns_in_place, connect_all_floor_regions_in_place, convert_hidden_walls_to_indestructible_in_place
from .features import place_features_in_place
from .prefabs import apply_prefab_pass_in_place, load_prefabs_from_json


class MapGenerator:
    def __init__(self, params: GenerationParams):
        self.params = params
        self.random = random.Random(params.seed)

    def generate(self, on_step: Optional[Callable[[MapData, str], None]] = None) -> MapData:
        p = self.params

        team_a = list(p.team_a_spawns)
        team_b = mirror_spawns_vertical(team_a, p.width) if p.mirror_spawns else []
        spawns: SpawnDict = {"team1": team_a, "team2": team_b}

        protected: Set[Tuple[int, int]] = set()
        for sx, sy in team_a + team_b:
            # protected disk around spawns (so CA/connectivity/features don't ruin them)
            for yy in range(sy - p.spawn_clear_radius, sy + p.spawn_clear_radius + 1):
                for xx in range(sx - p.spawn_clear_radius, sx + p.spawn_clear_radius + 1):
                    protected.add((xx, yy))

        def emit(stage: str) -> None:
            if on_step is not None:
                on_step(MapData(grid=grid, spawns=spawns), stage)

        # 1) CA base walls/floors
        grid = generate_ca_walls_grid(
            width=p.width,
            height=p.height,
            rng=self.random,
            initial_wall_prob=p.ca_initial_wall_prob,
            passes=p.ca_passes,
            birth_limit=p.ca_birth_limit,
            death_limit=p.ca_death_limit,
        )
        emit("base")

        # 2) Force-clear spawn zones (after CA too)
        for sx, sy in team_a + team_b:
            carve_disk(grid, sx, sy, p.spawn_clear_radius, tile="FL")
        emit("spawns")

        # 3) Ensure connectivity by carving corridors between spawns
        if p.enforce_connected_floor:
            # 3a) connect spawns (core paths)
            connect_spawns_in_place(
                grid=grid,
                spawns=(team_a + team_b),
                rng=self.random,
                corridor_radius=p.corridor_radius,
                protected_radius=p.spawn_clear_radius,
                extra_corridors=getattr(p, "extra_corridors", 0),
                extra_corridor_radius=getattr(p, "extra_corridor_radius", None),
            )

            # 3b) ensure ALL cave parts are connected (not only spawns)
            connect_all_floor_regions_in_place(
                grid=grid,
                spawns=(team_a + team_b),
                rng=self.random,
                corridor_radius=p.corridor_radius,
                protected_radius=p.spawn_clear_radius,
            )
            emit("corridors")

        # 3c) turn any walls not adjacent to floor into indestructible walls
        convert_hidden_walls_to_indestructible_in_place(grid)
        emit("hidden-walls")

        # 4) Place prefabs
        if getattr(p, "prefabs_enabled", True):
            prefabs = []
            path = getattr(p, "prefabs_json_path", "")
            if path:
                try:
                    prefabs = load_prefabs_from_json(path)
                except Exception as e:
                    # Fallback: no prefabs (and keep generation valid)
                    prefabs = []

            if prefabs:
                apply_prefab_pass_in_place(
                    grid=grid,
                    rng=self.random,
                    prefabs=prefabs,
                    category="STRUCTURE",
                    protected_centers=(team_a + team_b),
                    protected_radius=p.spawn_clear_radius,
                    on_apply=lambda _: emit("prefab-structure"),
                )
                apply_prefab_pass_in_place(
                    grid=grid,
                    rng=self.random,
                    prefabs=prefabs,
                    category="FEATURE",
                    protected_centers=(team_a + team_b),
                    protected_radius=p.spawn_clear_radius,
                    on_apply=lambda _: emit("prefab-feature"),
                )


        return MapData(grid=grid, spawns=spawns)
