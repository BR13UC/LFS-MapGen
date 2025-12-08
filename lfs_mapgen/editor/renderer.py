from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Tuple, List

import pygame

from lfs_mapgen.core.tiles import TILE_COLORS, PALETTE_TILES, TileId
from lfs_mapgen.core.types import MapData
from .config import RenderParams


# ---------------------------------------------------------------------------
# Editor-only constants
TILE_ASSET_DIR = Path("assets/tiles")
SPAWN_TOOL_T1 = "SPAWN_T1"
SPAWN_TOOL_T2 = "SPAWN_T2"
SPAWN_TOOL_ERASE = "SPAWN_ERASE"

EDITOR_PALETTE: List[str] = PALETTE_TILES + [
    SPAWN_TOOL_T1,
    SPAWN_TOOL_T2,
    SPAWN_TOOL_ERASE,
]

TILE_LABELS: Dict[str, str] = {
    "IW": "Indestr.",
    "WL": "Wall",
    "FL": "Floor",
    "WA": "Water",
    "HO": "Hole",
    "SP": "Spikes",
    SPAWN_TOOL_T1: "Spawn T1",
    SPAWN_TOOL_T2: "Spawn T2",
    SPAWN_TOOL_ERASE: "Erase spawn",
}

SPAWN_COLORS: Dict[str, Tuple[int, int, int]] = {
    "team1": (0, 255, 0),
    "team2": (255, 255, 0),
}

SPAWN_TOOL_COLORS: Dict[str, Tuple[int, int, int]] = {
    SPAWN_TOOL_T1: SPAWN_COLORS["team1"],
    SPAWN_TOOL_T2: SPAWN_COLORS["team2"],
    SPAWN_TOOL_ERASE: (160, 160, 160),
}

TILE_ASSET_DIR = Path("assets/tiles")


class PygameRenderer:
    """
    Handles drawing:
    - Map view (camera + zoom)
    - Sidebar palette (fixed size, independent from zoom)
    """

    def __init__(self, params: RenderParams) -> None:
        self.params = params
        self.map_data: Optional[MapData] = None

        self.camera_x: float = 0.0
        self.camera_y: float = 0.0

        self.selected_tile: TileId | str = "FL"

        self.font: Optional[pygame.font.Font] = None

        self.palette_items: List[str] = EDITOR_PALETTE

        # Fixed palette configuration (does not change with zoom)
        self.palette_tile_size: int = 32
        self.palette_offset_y: int = 0  # set by the app layout

        # Tile textures
        self.tile_images: Dict[str, pygame.Surface] = {}
        self._tile_images_loaded: bool = False

    # ------------------------------------------------------------------ API

    def set_map(self, map_data: MapData) -> None:
        self.map_data = map_data
        self.camera_x = 0.0
        self.camera_y = 0.0
        self._clamp_camera()

    def set_selected_tile(self, tile_id: TileId | str) -> None:
        self.selected_tile = tile_id

    def ensure_font(self) -> None:
        if self.font is None:
            self.font = pygame.font.SysFont("consolas", 16)

    def ensure_tile_images(self) -> None:
        """
        Load tile images from assets/tiles if present.
        One file per tile id, named '<ID>.png' (e.g. FL.png).
        """
        if self._tile_images_loaded:
            return
        self._tile_images_loaded = True

        if not TILE_ASSET_DIR.exists():
            return

        for tile_id in TILE_COLORS.keys():
            path = TILE_ASSET_DIR / f"{tile_id}.png"
            if path.exists():
                try:
                    img = pygame.image.load(path.as_posix()).convert_alpha()
                except pygame.error:
                    continue
                self.tile_images[tile_id] = img

    def _get_scaled_tile_image(self, tile_id: str, size: int) -> Optional[pygame.Surface]:
        img = self.tile_images.get(tile_id)
        if img is None:
            return None
        if img.get_width() == size and img.get_height() == size:
            return img
        return pygame.transform.smoothscale(img, (size, size))


    # ------------------------------------------------------------- Camera

    def move_camera(self, dx: float, dy: float) -> None:
        self.camera_x += dx
        self.camera_y += dy
        self._clamp_camera()

    def change_zoom(self, delta: int) -> None:
        if self.map_data is None:
            return

        screen = pygame.display.get_surface()
        if screen is None:
            return

        old_ts = self.params.tile_size
        new_ts = max(8, min(96, old_ts + delta))
        if new_ts == old_ts:
            return

        width, height = screen.get_size()
        sidebar_width = self.params.sidebar_width_px
        map_view_width_old = width - sidebar_width

        center_screen_x = map_view_width_old / 2
        center_screen_y = height / 2

        center_world_x = self.camera_x + center_screen_x
        center_world_y = self.camera_y + center_screen_y
        center_tile_x = center_world_x / old_ts
        center_tile_y = center_world_y / old_ts

        self.params.tile_size = new_ts

        map_view_width_new = width - sidebar_width
        self.camera_x = center_tile_x * new_ts - map_view_width_new / 2
        self.camera_y = center_tile_y * new_ts - height / 2

        self._clamp_camera()

    # -------------------------------------------------------- Coords helpers

    def is_in_map(self, x: int, y: int) -> bool:
        screen = pygame.display.get_surface()
        if screen is None:
            return False
        width, _ = screen.get_size()
        sidebar_width = self.params.sidebar_width_px
        return x < (width - sidebar_width)

    def is_in_palette(self, x: int, y: int) -> bool:
        screen = pygame.display.get_surface()
        if screen is None:
            return False
        width, _ = screen.get_size()
        sidebar_width = self.params.sidebar_width_px
        map_view_width = width - sidebar_width
        # palette is only the area on the right *below* palette_offset_y
        return x >= map_view_width and y >= self.palette_offset_y

    def get_map_coords_from_mouse(self, x: int, y: int) -> tuple[int, int]:
        tile_size = self.params.tile_size
        world_x = self.camera_x + x
        world_y = self.camera_y + y
        return int(world_x // tile_size), int(world_y // tile_size)

    def get_palette_index_from_mouse(self, x: int, y: int) -> int:
        screen = pygame.display.get_surface()
        if screen is None:
            return -1

        width, _ = screen.get_size()
        sidebar_width = self.params.sidebar_width_px
        palette_x = width - sidebar_width

        tile_size = self.palette_tile_size
        margin = 4

        if x < palette_x or y < self.palette_offset_y:
            return -1

        start_y = self.palette_offset_y + margin
        rel_y = y - start_y
        if rel_y < 0:
            return -1

        item_height = tile_size + margin
        index = rel_y // item_height
        return int(index)

    # ---------------------------------------------------------------- Draw

    def draw(self) -> None:
        screen = pygame.display.get_surface()
        if screen is None:
            return

        self.ensure_font()
        self.ensure_tile_images()
        assert self.font is not None

        width, height = screen.get_size()
        sidebar_width = self.params.sidebar_width_px

        map_view_rect = pygame.Rect(0, 0, width - sidebar_width, height)
        palette_rect = pygame.Rect(width - sidebar_width, 0, sidebar_width, height)

        screen.fill(self.params.background_color)

        if self.map_data is not None:
            self._draw_map(screen, map_view_rect)

        self._draw_palette(screen, palette_rect)

    def _get_scaled_tile_image(self, tile_id: str, size: int) -> Optional[pygame.Surface]:
        img = self.tile_images.get(tile_id)
        if img is None:
            return None
        if img.get_width() == size and img.get_height() == size:
            return img
        return pygame.transform.smoothscale(img, (size, size))

    def _draw_map(self, screen: pygame.Surface, map_view_rect: pygame.Rect) -> None:
        assert self.map_data is not None
        tile_size = self.params.tile_size

        h = len(self.map_data.grid)
        w = len(self.map_data.grid[0]) if h else 0

        spawn_lookup: Dict[tuple[int, int], str] = {}
        for team, coords in self.map_data.spawns.items():
            for cx, cy in coords:
                spawn_lookup[(cx, cy)] = team

        for ty in range(h):
            for tx in range(w):
                tile_id = self.map_data.grid[ty][tx]
                color = TILE_COLORS.get(tile_id, (255, 0, 255))

                world_x = tx * tile_size
                world_y = ty * tile_size

                sx = int(world_x - self.camera_x)
                sy = int(world_y - self.camera_y)

                rect = pygame.Rect(sx, sy, tile_size, tile_size)
                if not map_view_rect.colliderect(rect):
                    continue

                # try texture, fallback to solid color
                img = self._get_scaled_tile_image(tile_id, tile_size)
                if img is not None:
                    screen.blit(img, rect)
                else:
                    pygame.draw.rect(screen, color, rect)

                if self.params.show_grid:
                    pygame.draw.rect(screen, (30, 30, 30), rect, 1)

                key = (tx, ty)
                if key in spawn_lookup:
                    team = spawn_lookup[key]
                    scolor = SPAWN_COLORS.get(team, (255, 255, 255))
                    marker_size = max(4, tile_size // 3)
                    marker_rect = pygame.Rect(0, 0, marker_size, marker_size)
                    marker_rect.center = rect.center
                    pygame.draw.rect(screen, scolor, marker_rect)

    def _draw_palette(self, screen: pygame.Surface, palette_rect: pygame.Rect) -> None:
        tile_size = self.palette_tile_size
        margin = 4
        pygame.draw.rect(screen, (10, 10, 10), palette_rect)

        self.ensure_font()
        assert self.font is not None

        start_y = max(self.palette_offset_y, palette_rect.y) + margin

        for i, tile_id in enumerate(self.palette_items):
            y = start_y + i * (tile_size + margin)
            x = palette_rect.x + margin

            tile_rect = pygame.Rect(x, y, tile_size, tile_size)

            if tile_id in TILE_COLORS:
                color = TILE_COLORS.get(tile_id, (255, 0, 255))
                img = self._get_scaled_tile_image(tile_id, tile_size)
                if img is not None:
                    pygame.draw.rect(screen, (0, 0, 0), tile_rect)  # small bg
                    screen.blit(img, tile_rect)
                else:
                    pygame.draw.rect(screen, color, tile_rect)
            elif tile_id in SPAWN_TOOL_COLORS:
                color = SPAWN_TOOL_COLORS[tile_id]
                pygame.draw.rect(screen, color, tile_rect)
            else:
                pygame.draw.rect(screen, (255, 0, 255), tile_rect)

            if tile_id == self.selected_tile:
                pygame.draw.rect(screen, (255, 255, 0), tile_rect, 3)
            else:
                pygame.draw.rect(screen, (60, 60, 60), tile_rect, 1)

            label = TILE_LABELS.get(tile_id, tile_id)
            text_surf = self.font.render(label, True, (220, 220, 220))
            text_rect = text_surf.get_rect(
                midleft=(tile_rect.right + 8, tile_rect.centery)
            )
            screen.blit(text_surf, text_rect)


    # -------------------------------------------------------------- internals

    def _clamp_camera(self) -> None:
        if self.map_data is None:
            self.camera_x = 0
            self.camera_y = 0
            return

        screen = pygame.display.get_surface()
        if screen is None:
            return

        width, height = screen.get_size()
        tile_size = self.params.tile_size
        sidebar_width = self.params.sidebar_width_px
        map_view_width = max(1, width - sidebar_width)
        map_view_height = height

        map_w_px = len(self.map_data.grid[0]) * tile_size
        map_h_px = len(self.map_data.grid) * tile_size

        max_x = max(0, map_w_px - map_view_width)
        max_y = max(0, map_h_px - map_view_height)

        self.camera_x = max(0, min(self.camera_x, max_x))
        self.camera_y = max(0, min(self.camera_y, max_y))
