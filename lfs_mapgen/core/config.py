from __future__ import annotations
from dataclasses import dataclass


@dataclass
class GenerationParams:
    width: int = 40
    height: int = 40
    seed: int = 0
    floor_percent: float = 0.55
    wall_percent: float = 0.1
    breakable_wall_percent: float = 0.1
    water_percent: float = 0.1
    holes_percent: float = 0.05
    spikes_percent: float = 0.1
    enforce_connected_floor: bool = True
