"""Repo entrypoint.

Keeps `python main.py` working while using an industry-standard `src/` layout.
"""

from __future__ import annotations

import os
import sys


def _ensure_src_on_path() -> None:
    """src 디렉토리를 sys.path에 추가 (개발 환경 및 PyInstaller 환경 모두 지원)"""
    # PyInstaller로 빌드된 경우
    if getattr(sys, 'frozen', False):
        # PyInstaller는 pathex=['src']를 사용하여 분석 시 모듈을 찾지만,
        # 번들에는 디렉토리 구조를 보존하지 않습니다.
        # study_with 패키지는 이미 번들에 포함되어 있어 추가 경로 설정이 필요 없습니다.
        pass
    else:
        # 개발 환경
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
