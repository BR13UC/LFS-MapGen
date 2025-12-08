from __future__ import annotations
from lfs_mapgen.editor.config import AppConfig
from lfs_mapgen.editor.app import MapGenApp


def main():
    app = MapGenApp(AppConfig())
    app.run()


if __name__ == "__main__":
    main()
