from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class GenerationParams:
    # Size
    width: int = 60
    height: int = 30

    # RNG
    seed: Optional[int] = None

    # Spawns (team B is mirrored from team A)
    team_a_spawns: List[Tuple[int, int]] = field(
        default_factory=lambda: [
            (6, 11),
            (6, 15),
            (6, 19),
        ]
    )
    mirror_spawns: bool = True

    # Spawn protection
    spawn_clear_radius: int = 3

    # Cellular Automata (walls)
    ca_initial_wall_prob: float = 0.45
    ca_passes: int = 5
    ca_birth_limit: int = 5
    ca_death_limit: int = 3

    # Connectivity carving
    enforce_connected_floor: bool = True
    corridor_radius: int = 1

    # Features (placed after connectivity)
    water_percent: float = 0.01
    holes_percent: float = 0.005
    spikes_percent: float = 0.01

    extra_corridors: int = 4
    extra_corridor_radius: int = 2

    # Prefabs
    prefabs_enabled: bool = True
    prefabs_json_path: str = "assets/prefabs/prefabs.json"


