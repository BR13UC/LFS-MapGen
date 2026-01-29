from __future__ import annotations

from lfs_mapgen.core.config import GenerationParams
from lfs_mapgen.core.generators import MapGenerator
from lfs_mapgen.core.io import save_map


def main():
    params = GenerationParams(width=40, height=30)
    gen = MapGenerator(params)
    data = gen.generate()

    save_map("cli_generated_map", data, params)
    print("CLI map generated as maps/cli_generated_map.json")


if __name__ == "__main__":
    main()
