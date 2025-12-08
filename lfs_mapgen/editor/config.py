from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from lfs_mapgen.core.config import GenerationParams


@dataclass
class RenderParams:
    tile_size: int = 32
    window_title: str = "LFS MapGen - Editor"
    show_grid: bool = True
    # Sidebar has a constant pixel width, independent of zoom
    sidebar_width_px: int = 220
    background_color: Tuple[int, int, int] = (15, 15, 20)


@dataclass
class AppConfig:
    generation: GenerationParams = field(default_factory=GenerationParams)
    render: RenderParams = field(default_factory=RenderParams)
