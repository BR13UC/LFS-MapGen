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

        # --- spawn inputs (Team A) -----------------------------------------
        self.spawn_inputs_a: list[tuple[TextInput, TextInput]] = []

        defaults = self.cfg.generation.team_a_spawns

        for i in range(3):
            x, y = defaults[i]
            self.spawn_inputs_a.append((
                TextInput(
                    rect=pygame.Rect(0, 0, 10, 10),
                    font=self.font,
                    text=str(x),
                    placeholder="x",
                    max_length=3,
                ),
                TextInput(
                    rect=pygame.Rect(0, 0, 10, 10),
                    font=self.font,
                    text=str(y),
                    placeholder="y",
                    max_length=3,
                ),
            ))

        # order = order in sidebar
        self.tile_inputs = [
            self.input_width,
            self.input_height
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
        h_input = 28
        gap = 8
        bottom_margin = 10

        # --- top buttons ------------------------------------------------------
        self.btn_generate.rect = pygame.Rect(x, y, w, h_btn)
        y += h_btn + gap

        self.btn_save.rect = pygame.Rect(x, y, w, h_btn)
        y += h_btn + gap

        self.save_name_input.rect = pygame.Rect(x, y, w, h_btn)
        y += h_btn + gap

        self.dropdown_load.rect = pygame.Rect(x, y, w, h_btn)
        y += h_btn + gap

        # --- spawns (Team A) --------------------------------------------------
        for x_in, y_in in self.spawn_inputs_a:
            x_in.rect = pygame.Rect(x, y, (w - gap) // 2, h_input)
            y_in.rect = pygame.Rect(x + (w + gap) // 2, y, (w - gap) // 2, h_input)
            y += h_input + gap

        # palette starts below buttons + spawns, and above bottom inputs
        self.renderer.palette_offset_y = y + 4

        # --- bottom inputs block (tile % + map size, etc.) --------------------
        bottom_inputs_count = len(self.tile_inputs)
        if bottom_inputs_count > 0:
            bottom_block_h = bottom_inputs_count * h_input + (bottom_inputs_count - 1) * gap
        else:
            bottom_block_h = 0

        # available vertical space for palette
        available_palette_h = (
            height
            - self.renderer.palette_offset_y
            - gap
            - bottom_block_h
            - bottom_margin
        )

        # --- autoscale palette tile size to prevent overlap -------------------
        n_items = max(1, len(self.renderer.palette_items))
        default_tile_size = self.cfg.render.palette_tile_size_px if hasattr(self.cfg.render, "palette_tile_size_px") else self.renderer.palette_tile_size

        # palette_height ~= 8 + n_items * (tile_size + 4)
        computed_tile_size = int((max(0, available_palette_h) - 8) / n_items - 4)

        # clamp to keep it usable
        self.renderer.palette_tile_size = max(16, min(default_tile_size, computed_tile_size))

        # final palette height with resized tile size
        palette_item_h = self.renderer.palette_tile_size + 4
        palette_height = 8 + n_items * palette_item_h

        # --- place bottom inputs right after palette --------------------------
        y_inputs = self.renderer.palette_offset_y + palette_height + gap
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

        # map size from sidebar
        g.width = parse_int(self.input_width.text, g.width, 5, 200)
        g.height = parse_int(self.input_height.text, g.height, 5, 200)

        # team A spawns from sidebar (keep this if you still want spawn inputs)
        g.team_a_spawns = self._read_team_a_spawns()

    def generate_map(self) -> None:
        self._update_generation_params_from_inputs()
        gen = MapGenerator(self.cfg.generation)
        self.map_data = gen.generate(on_step=self._render_generation_step)
        self.renderer.set_map(self.map_data)

    def _render_generation_step(self, map_data: MapData, stage: str) -> None:
        self.map_data = map_data
        self.renderer.set_map(map_data)
        self.renderer.draw()
        self.draw_ui()
        pygame.display.flip()
        pygame.event.pump()

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
            for x_in, y_in in self.spawn_inputs_a:
                x_in.handle_event(event)
                y_in.handle_event(event)

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
        for x_in, y_in in self.spawn_inputs_a:
            x_in.handle_event(event)
            y_in.handle_event(event)

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
        for x_in, y_in in self.spawn_inputs_a:
            x_in.draw(self.window)
            y_in.draw(self.window)

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
                    for x_in, y_in in self.spawn_inputs_a:
                        x_in.handle_event(event)
                        y_in.handle_event(event)

            self.renderer.draw()
            self.draw_ui()
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def _read_team_a_spawns(self) -> list[tuple[int, int]]:
        w = self.cfg.generation.width
        h = self.cfg.generation.height

        out: list[tuple[int, int]] = []
        used = set()

        for x_in, y_in in self.spawn_inputs_a:
            try:
                x = int(x_in.text)
            except ValueError:
                x = 0
            try:
                y = int(y_in.text)
            except ValueError:
                y = 0

            x = max(0, min(w - 1, x))
            y = max(0, min(h - 1, y))

            # éviter doublons
            while (x, y) in used:
                x = min(w - 1, x + 1)

            used.add((x, y))
            out.append((x, y))

        return out
