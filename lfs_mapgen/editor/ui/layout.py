from __future__ import annotations

from typing import Iterator, Tuple
import pygame


def hstack(rect: pygame.Rect, count: int, margin: int = 4) -> Iterator[pygame.Rect]:
    total_margin = margin * (count - 1)
    width = (rect.width - total_margin) // count
    x = rect.x
    for _ in range(count):
        yield pygame.Rect(x, rect.y, width, rect.height)
        x += width + margin


def vstack(rect: pygame.Rect, count: int, margin: int = 4) -> Iterator[pygame.Rect]:
    total_margin = margin * (count - 1)
    height = (rect.height - total_margin) // count
    y = rect.y
    for _ in range(count):
        yield pygame.Rect(rect.x, y, rect.width, height)
        y += height + margin
