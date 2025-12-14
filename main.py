"""Repo entrypoint.

Keeps `python main.py` working while using an industry-standard `src/` layout.
"""

from __future__ import annotations

import os
import sys


def _ensure_src_on_path() -> None:
    repo_root = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(repo_root, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)


def main() -> None:
    _ensure_src_on_path()
    from study_with.app import main as _app_main

    _app_main()


if __name__ == "__main__":
    main()
