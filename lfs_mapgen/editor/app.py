from __future__ import annotations

import sys
from typing import Optional

import pygame

from lfs_mapgen.core.generation import MapGenerator
from lfs_mapgen.core.io import list_maps, load_map, save_map
from lfs_mapgen.core.tiles import TileId
from lfs_mapgen.core.types import MapData

from .config import AppConfig
from .renderer import (
    PygameRenderer,
    SPAWN_TOOL_T1,
    SPAWN_TOOL_T2,
    SPAWN_TOOL_ERASE,
)
from .ui.widgets import Button, TextInput, MenuDropDown


class MapGenApp:
    def __init__(self, config: AppConfig) -> None:
        self.cfg = config
        self.renderer = PygameRenderer(config.render)
        self.map_data: Optional[MapData] = None

        pygame.init()
        pygame.display.set_caption(self.cfg.render.window_title)

        self.window = pygame.display.set_mode((1200, 800), pygame.RESIZABLE)
        self.font = pygame.font.SysFont("consolas", 18)

        self.btn_generate = Button(
            rect=pygame.Rect(0, 0, 10, 10),
            text="Generate Map",
            font=self.font,
            on_click=self.generate_map,
        )
        self.btn_save = Button(
            rect=pygame.Rect(0, 0, 10, 10),
            text="Save",
            font=self.font,
            on_click=self.save_current_map,
        )
        self.save_name_input = TextInput(
            rect=pygame.Rect(0, 0, 10, 10),
            font=self.font,
            text="",
            placeholder="map name...",
        )
        self.dropdown_load = MenuDropDown(
            rect=pygame.Rect(0, 0, 10, 10),
            font=self.font,
            label="Load",
        )

        g = self.cfg.generation

        def pct(v: float) -> str:
            return str(int(v * 100))

        # --- map size inputs -------------------------------------------------
        self.input_width = TextInput(
            rect=pygame.Rect(0, 0, 10, 10),
            font=self.font,
            text=str(g.width),
            placeholder="Width",
            max_length=4,
        )
        self.input_height = TextInput(
            rect=pygame.Rect(0, 0, 10, 10),
            font=self.font,
            text=str(g.height),
            placeholder="Height",
            max_length=4,
        )

        # --- tile percentage inputs -----------------------------------------
        self.input_floor = TextInput(
            rect=pygame.Rect(0, 0, 10, 10),
            font=self.font,
            text=pct(g.floor_percent),
            placeholder="Floor%",
        )
        self.input_wall_iw = TextInput(
            rect=pygame.Rect(0, 0, 10, 10),
            font=self.font,
            text=pct(g.wall_percent),
            placeholder="Indestr.%",
        )
        self.input_wall_wl = TextInput(
            rect=pygame.Rect(0, 0, 10, 10),
            font=self.font,
            text=pct(g.breakable_wall_percent),
            placeholder="Wall%",
        )
        self.input_water = TextInput(
            rect=pygame.Rect(0, 0, 10, 10),
            font=self.font,
            text=pct(g.water_percent),
            placeholder="Water%",
        )
        self.input_holes = TextInput(
            rect=pygame.Rect(0, 0, 10, 10),
            font=self.font,
            text=pct(g.holes_percent),
            placeholder="Hole%",
        )
        self.input_spikes = TextInput(
            rect=pygame.Rect(0, 0, 10, 10),
            font=self.font,
            text=pct(g.spikes_percent),
            placeholder="Spikes%",
        )

        # order = order in sidebar
        self.tile_inputs = [
            self.input_width,
            self.input_height,
            self.input_floor,
            self.input_wall_iw,
            self.input_wall_wl,
            self.input_water,
            self.input_holes,
            self.input_spikes,
        ]

        self.update_load_dropdown()
        self._layout_ui()

        # camera dragging
        self.dragging = False
        self.drag_start = (0, 0)

    # ---------------------------------------------------------------- Layout

    def _layout_ui(self) -> None:
        width, height = self.window.get_size()
        sidebar_width = self.cfg.render.sidebar_width_px

        x = width - sidebar_width + 10
        w = sidebar_width - 20
        y = 10
        h_btn = 32
        gap = 8

        # buttons
        self.btn_generate.rect = pygame.Rect(x, y, w, h_btn)
        y += h_btn + gap

        self.btn_save.rect = pygame.Rect(x, y, w, h_btn)
        y += h_btn + gap

        self.save_name_input.rect = pygame.Rect(x, y, w, h_btn)
        y += h_btn + gap

        self.dropdown_load.rect = pygame.Rect(x, y, w, h_btn)
        y += h_btn + gap

        # palette starts below buttons + load, and above tile % inputs
        self.renderer.palette_offset_y = y + 4

        # height of palette so we can place inputs after it
        palette_item_h = self.renderer.palette_tile_size + 4
        palette_height = 4 + len(self.renderer.palette_items) * palette_item_h + 4

        y_inputs = self.renderer.palette_offset_y + palette_height + gap

        # tile percentage inputs stacked at the bottom of the sidebar
        h_input = 28
        for inp in self.tile_inputs:
            inp.rect = pygame.Rect(x, y_inputs, w, h_input)
            y_inputs += h_input + gap

    # ---------------------------------------------------------------- UI data

    def update_load_dropdown(self) -> None:
        names = list_maps()
        items = []
        for n in names:
            def load_closure(name=n):
                self.load_map_by_name(name)
            items.append((n, load_closure))
        self.dropdown_load.set_items(items)

    # -------------------------------------------------------------- Generation

    def _update_generation_params_from_inputs(self) -> None:
        def parse_percent(text: str, fallback: float) -> float:
            text = text.strip()
            if not text:
                return fallback
            try:
                val = float(text)
            except ValueError:
                return fallback
            if val > 1.0:
                val /= 100.0
            return max(0.0, min(1.0, val))

        def parse_int(text: str, fallback: int, min_val: int, max_val: int) -> int:
            text = text.strip()
            if not text:
                return fallback
            try:
                val = int(text)
            except ValueError:
                return fallback
            return max(min_val, min(max_val, val))

        g = self.cfg.generation

        # --- new: map size from sidebar ------------------------------------
        g.width = parse_int(self.input_width.text, g.width, 5, 200)
        g.height = parse_int(self.input_height.text, g.height, 5, 200)

        # existing tile percentages
        g.floor_percent = parse_percent(self.input_floor.text, g.floor_percent)
        g.wall_percent = parse_percent(self.input_wall_iw.text, g.wall_percent)
        g.breakable_wall_percent = parse_percent(
            self.input_wall_wl.text, g.breakable_wall_percent
        )
        g.water_percent = parse_percent(self.input_water.text, g.water_percent)
        g.holes_percent = parse_percent(self.input_holes.text, g.holes_percent)
        g.spikes_percent = parse_percent(self.input_spikes.text, g.spikes_percent)


    def generate_map(self) -> None:
        self._update_generation_params_from_inputs()
        gen = MapGenerator(self.cfg.generation)
        self.map_data = gen.generate()
        self.renderer.set_map(self.map_data)

    # ----------------------------------------------------------------- IO

    def save_current_map(self) -> None:
        if self.map_data is None:
            print("No map to save.")
            return

        name = self.save_name_input.text.strip()
        if not name:
            print("Please enter a map name first.")
            return

        save_map(name, self.map_data, self.cfg.generation)
        print(f"Saved map '{name}'.")
        self.update_load_dropdown()

    def load_map_by_name(self, name: str) -> None:
        try:
            data = load_map(name)
        except FileNotFoundError:
            print(f"Map '{name}' does not exist.")
            return

        grid = data.get("grid", [])
        spawns = data.get("spawns", {})
        self.map_data = MapData(grid=grid, spawns=spawns)
        self.renderer.set_map(self.map_data)
        print(f"Loaded map '{name}'.")

    # -------------------------------------------------------------- Tools

    def _apply_tool_at(self, tile_x: int, tile_y: int) -> None:
        if not self.map_data:
            return

        coord = (tile_x, tile_y)
        selected = self.renderer.selected_tile

        if selected == SPAWN_TOOL_T1:
            lst = self.map_data.spawns.setdefault("team1", [])
            if coord not in lst:
                lst.append(coord)
        elif selected == SPAWN_TOOL_T2:
            lst = self.map_data.spawns.setdefault("team2", [])
            if coord not in lst:
                lst.append(coord)
        elif selected == SPAWN_TOOL_ERASE:
            for team, coords in list(self.map_data.spawns.items()):
                self.map_data.spawns[team] = [c for c in coords if c != coord]
        else:
            self.map_data.grid[tile_y][tile_x] = selected  # type: ignore[assignment]

    # -------------------------------------------------------------- Events

    def handle_mouse_down(self, event: pygame.event.Event) -> None:
        x, y = event.pos

        if self.dropdown_load.open:
            return

        if event.button == 1:
            # send to UI first
            self.btn_generate.handle_event(event)
            self.btn_save.handle_event(event)
            self.save_name_input.handle_event(event)
            self.dropdown_load.handle_event(event)
            for inp in self.tile_inputs:
                inp.handle_event(event)

            # palette selection
            if self.renderer.is_in_palette(x, y):
                index = self.renderer.get_palette_index_from_mouse(x, y)
                if 0 <= index < len(self.renderer.palette_items):
                    tile_id: TileId | str = self.renderer.palette_items[index]
                    self.renderer.set_selected_tile(tile_id)
                return

            # painting on map
            if self.map_data and self.renderer.is_in_map(x, y):
                tile_x, tile_y = self.renderer.get_map_coords_from_mouse(x, y)
                if (
                    0 <= tile_y < len(self.map_data.grid)
                    and 0 <= tile_x < len(self.map_data.grid[0])
                ):
                    self._apply_tool_at(tile_x, tile_y)
                return

        # right or middle button: start camera drag
        if event.button in (2, 3) and self.renderer.is_in_map(x, y):
            self.dragging = True
            self.drag_start = event.pos

    def handle_mouse_up(self, event: pygame.event.Event) -> None:
        if event.button in (2, 3):
            self.dragging = False

    def handle_mouse_motion(self, event: pygame.event.Event) -> None:
        # UI hover
        self.btn_generate.handle_event(event)
        self.btn_save.handle_event(event)
        self.save_name_input.handle_event(event)
        self.dropdown_load.handle_event(event)
        for inp in self.tile_inputs:
            inp.handle_event(event)

        x, y = event.pos

        if self.dragging:
            dx = -event.rel[0]
            dy = -event.rel[1]
            self.renderer.move_camera(dx, dy)
            return

        # painting while holding left button
        if (
            event.buttons[0]
            and self.map_data
            and self.renderer.is_in_map(x, y)
        ):
            tile_x, tile_y = self.renderer.get_map_coords_from_mouse(x, y)
            if (
                0 <= tile_y < len(self.map_data.grid)
                and 0 <= tile_x < len(self.map_data.grid[0])
            ):
                self._apply_tool_at(tile_x, tile_y)

    def handle_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_r:
            self.renderer.camera_x = 0
            self.renderer.camera_y = 0

    def handle_mouse_wheel(self, event: pygame.event.Event) -> None:
        # zoom only when over map, not over sidebar
        x, y = pygame.mouse.get_pos()
        if self.renderer.is_in_map(x, y):
            self.renderer.change_zoom(event.y)

    # ----------------------------------------------------------- Draw UI

    def draw_ui(self) -> None:
        self.btn_generate.draw(self.window)
        self.btn_save.draw(self.window)
        self.save_name_input.draw(self.window)
        self.dropdown_load.draw(self.window)
        for inp in self.tile_inputs:
            inp.draw(self.window)

    # ------------------------------------------------------------- Main loop

    def run(self) -> None:
        clock = pygame.time.Clock()
        running = True

        while running:
            _dt = clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type == pygame.VIDEORESIZE:
                    self.window = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                    self._layout_ui()
                    continue

                self.dropdown_load.handle_event(event)

                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_down(event)

                if event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(event)

                if event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event)

                if event.type == pygame.MOUSEWHEEL:
                    self.handle_mouse_wheel(event)

                if event.type == pygame.KEYDOWN:
                    self.handle_key(event)
                    self.save_name_input.handle_event(event)
                    for inp in self.tile_inputs:
                        inp.handle_event(event)

            self.renderer.draw()
            self.draw_ui()
            pygame.display.flip()

        pygame.quit()
        sys.exit()
