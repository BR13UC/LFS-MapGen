from __future__ import annotations

from typing import Callable, List, Any, Optional
import pygame


class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        on_click: Callable[[], None],
    ) -> None:
        self.rect = rect
        self.text = text
        self.font = font
        self.on_click = on_click
        self.hover: bool = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()

    def draw(self, surface: pygame.Surface) -> None:
        base_color = (70, 70, 80)
        hover_color = (100, 100, 120)
        color = hover_color if self.hover else base_color

        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        pygame.draw.rect(surface, (20, 20, 20), self.rect, 1, border_radius=4)

        text_surf = self.font.render(self.text, True, (240, 240, 240))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class TextInput:
    def __init__(
        self,
        rect: pygame.Rect,
        font: pygame.font.Font,
        text: str = "",
        placeholder: str = "",
        max_length: int = 32,
    ) -> None:
        self.rect = rect
        self.font = font
        self.text = text
        self.placeholder = placeholder
        self.active: bool = False
        self.max_length = max_length

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                if len(self.text) < self.max_length and event.unicode.isprintable():
                    self.text += event.unicode

    def draw(self, surface: pygame.Surface) -> None:
        bg_color = (30, 30, 40) if self.active else (20, 20, 30)
        border_color = (200, 200, 255) if self.active else (80, 80, 100)

        pygame.draw.rect(surface, bg_color, self.rect, border_radius=4)
        pygame.draw.rect(surface, border_color, self.rect, 1, border_radius=4)

        display_text = self.text if self.text else self.placeholder
        color = (240, 240, 240) if self.text else (150, 150, 170)

        text_surf = self.font.render(display_text, True, color)
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 6, self.rect.centery))
        surface.blit(text_surf, text_rect)


class MenuDropDown:
    """
    Simple dropdown menu.
    items: list of (label, callback)
    """

    def __init__(
        self,
        rect: pygame.Rect,
        font: pygame.font.Font,
        items: Optional[List[tuple[str, Callable[[], None]]]] = None,
        label: str = "Menu",
    ) -> None:
        self.rect = rect
        self.font = font
        self.items: List[tuple[str, Callable[[], None]]] = items or []
        self.label = label
        self.open: bool = False
        self.hover: bool = False

    def set_items(self, items: List[tuple[str, Callable[[], None]]]) -> None:
        self.items = items

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                # toggle menu
                self.open = not self.open
                return

            if self.open:
                # click in items list?
                x, y = event.pos
                item_height = self.rect.height
                list_rect = pygame.Rect(
                    self.rect.x,
                    self.rect.y + self.rect.height,
                    self.rect.width + 80,
                    item_height * len(self.items),
                )
                if list_rect.collidepoint(event.pos):
                    rel_y = y - list_rect.y
                    index = int(rel_y // item_height)
                    if 0 <= index < len(self.items):
                        _label, cb = self.items[index]
                        cb()
                    self.open = False
                else:
                    # click outside closes menu
                    self.open = False

    def draw(self, surface: pygame.Surface) -> None:
        base_color = (60, 60, 80)
        hover_color = (90, 90, 120)
        color = hover_color if self.hover or self.open else base_color

        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        pygame.draw.rect(surface, (20, 20, 20), self.rect, 1, border_radius=4)

        label = f"{self.label} ▼"
        text_surf = self.font.render(label, True, (240, 240, 240))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

        if self.open and self.items:
            item_height = self.rect.height
            list_rect = pygame.Rect(
                self.rect.x,
                self.rect.y + self.rect.height,
                self.rect.width + 80,
                item_height * len(self.items),
            )
            pygame.draw.rect(surface, (25, 25, 35), list_rect)
            pygame.draw.rect(surface, (10, 10, 10), list_rect, 1)

            for i, (label, _cb) in enumerate(self.items):
                item_rect = pygame.Rect(
                    list_rect.x,
                    list_rect.y + i * item_height,
                    list_rect.width,
                    item_height,
                )
                pygame.draw.rect(surface, (40, 40, 55), item_rect)
                text_surf = self.font.render(label, True, (230, 230, 230))
                text_rect = text_surf.get_rect(midleft=(item_rect.x + 6, item_rect.centery))
                surface.blit(text_surf, text_rect)


def draw_label(surface: pygame.Surface, font: pygame.font.Font, text: str, x: int, y: int) -> None:
    text_surf = font.render(text, True, (220, 220, 220))
    surface.blit(text_surf, (x, y))
