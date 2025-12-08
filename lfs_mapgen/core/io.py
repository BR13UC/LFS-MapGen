from __future__ import annotations
import json
from pathlib import Path
from dataclasses import asdict
from typing import Any, Dict
from .types import MapData
from .config import GenerationParams

SAVE_DIR = Path("maps")
SAVE_DIR.mkdir(exist_ok=True)


def save_map(name: str, map_data: MapData, params: GenerationParams) -> Path:
    """
    Save a map as JSON in the maps/ folder.
    Always saves as <name>.json (extension added if not present).
    """
    if not name:
        name = "unnamed"

    path = SAVE_DIR / name
    if path.suffix != ".json":
        path = path.with_suffix(".json")

    payload: Dict[str, Any] = {
        "width": len(map_data.grid[0]) if map_data.grid else 0,
        "height": len(map_data.grid),
        "grid": map_data.grid,
        "spawns": map_data.spawns,
        "generation_params": asdict(params),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)

    return path


def load_map(name: str) -> Dict[str, Any]:
    """
    Load a JSON map from the maps/ folder.
    - If 'name' has no extension, '.json' is added.
    - If 'name' already has an extension, it is used as-is.
    """
    path = SAVE_DIR / name
    if path.suffix == "":
        path = path.with_suffix(".json")

    if not path.exists():
        raise FileNotFoundError(f"Map '{name}' not found at {path}.")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_maps() -> list[str]:
    """
    List ALL files in maps/, not just .json.
    Returns file names (including extension).
    """
    return sorted([p.name for p in SAVE_DIR.iterdir() if p.is_file()])
