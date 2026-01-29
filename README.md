# LFS-MapGen

A map generator and lightweight editor for the LearnFromScraps game.

## Table of contents
- [Features](#features)
- [Quick start](#quick-start)
- [Project layout](#project-layout)
- [Generation pipeline](#generation-pipeline)
- [Procedural tools](#procedural-tools)
- [Configuration](#configuration)
- [Output format](#output-format)
- [Tiles](#tiles)
- [Prefabs](#prefabs)

## Features
- Pygame-based editor for generating, viewing, and saving maps.
- CLI helper to generate a sample map JSON.
- Deterministic map generation via seeded parameters.
- Procedural pipeline that combines cellular automata, connectivity carving, and prefab stamping.

## Quick start
### Run the editor
```bash
python main.py
```

The editor lets you generate a map, paint tiles, edit spawn points, and save to the `maps/` directory.

### Generate a map via CLI
```bash
python cli_generate.py
```

The CLI script creates a map and saves it under `maps/`.

## Project layout
- `main.py`: launches the Pygame editor app.
- `cli_generate.py`: CLI helper that generates a map JSON.
- `lfs_mapgen/core`: core generation logic (configuration, pipeline, prefab rules, IO).
- `lfs_mapgen/editor`: Pygame editor UI and rendering.
- `assets/prefabs/prefabs.json`: prefab definitions applied during generation.
- `maps/`: output directory for generated and saved maps.

## Generation pipeline
The generator runs through a small pipeline:
1. Build a base wall/floor grid using cellular automata.
2. Clear spawn disks to ensure safe starting zones.
3. Carve corridors to connect spawns and any disconnected floor regions.
4. Convert hidden walls to indestructible walls.
5. Apply prefab passes for structure and feature placement.

## Procedural tools
The generator combines multiple procedural techniques to build playable maps:

- **Cellular automata cave carving**: a randomized wall/floor grid is evolved with birth/death limits to create organic cave shapes.
- **Spawn mirroring and protection**: team spawns can be mirrored for symmetry, and spawn zones are cleared/kept open during generation.
- **Connectivity carving**: A* corridors connect spawn points and any remaining disconnected floor regions, with optional extra corridors for variety.
- **Hidden-wall conversion**: walls that never touch floors are converted into indestructible walls to avoid trapped voids.
- **Prefab stamping**: JSON-driven prefabs (with rotation variants and reserved spacing) are stamped onto the grid to add structure and features.

## Configuration
Generation settings live in `GenerationParams` and include:
- Map size and seed.
- Team A spawns (Team B is optionally mirrored).
- Spawn clear radius.
- Cellular automata parameters (initial wall probability, passes, birth/death limits).
- Connectivity and corridor radius settings.
- Optional extra corridors.
- Prefab enablement and prefab JSON path.

Update values in `GenerationParams` (or editor inputs) to tune output.

## Output format
Generated maps are written as JSON with:
- `width` and `height`.
- `grid`: 2D array of tile IDs.
- `spawns`: team spawn coordinates.
- `generation_params`: the parameters used for generation.

## Tiles
Tile IDs used in the grid:
- `IW`: Inbreakable Wall
- `WL`: Wall
- `FL`: Floor
- `WA`: Water
- `HO`: Hole
- `SP`: Spikes

## Prefabs
Prefab JSON is loaded from `assets/prefabs/prefabs.json` and supports:
- `STRUCTURE` and `FEATURE` categories.
- `before` token matching (e.g., `SOLID`, `MT:FLOOR`).
- `after` patches that swap logical tiles to real tile IDs.
- Optional `reserve` rectangles and rotation variants to avoid overlaps.
