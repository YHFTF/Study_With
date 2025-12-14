"""Repo convenience entrypoint.

Kept for backwards compatibility: `python clean_hosts.py`.
"""

from __future__ import annotations

import os
import runpy


if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.abspath(__file__))
    runpy.run_path(os.path.join(repo_root, "scripts", "clean_hosts.py"), run_name="__main__")
