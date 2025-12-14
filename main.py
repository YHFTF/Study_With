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
        # exe 파일이 있는 디렉토리
        if hasattr(sys, '_MEIPASS'):
            # 임시 디렉토리에서 실행 중
            base_path = sys._MEIPASS
        else:
            # onefile 모드가 아닌 경우
            base_path = os.path.dirname(sys.executable)
        
        # src 디렉토리 찾기
        src_dir = os.path.join(base_path, "src")
        if os.path.exists(src_dir) and src_dir not in sys.path:
            sys.path.insert(0, src_dir)
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
