"""클라우드 서버(Study With Cloud Server)와 통신하는 클라이언트 유틸."""

from __future__ import annotations

import json
import os
import platform
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _get_config_dir() -> Path:
    """OS별 설정 파일 저장 디렉토리 반환 (app.py와 동일 규칙)."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        config_dir = base / "StudyWith" / "config"
    elif system == "Darwin":
        config_dir = Path.home() / "Library" / "Application Support" / "StudyWith" / "config"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
        config_dir = base / "study-with" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _auth_file() -> Path:
    return _get_config_dir() / "cloud_auth.json"


def _normalize_base_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    # trailing slash 제거
    while url.endswith("/"):
        url = url[:-1]
    return url


class CloudError(RuntimeError):
    pass


@dataclass
class CloudAuth:
    base_url: str = ""
    token: str = ""
    username: str = ""

    @classmethod
    def load(cls) -> "CloudAuth":
        p = _auth_file()
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return cls(
                base_url=_normalize_base_url(str(data.get("base_url", ""))),
                token=str(data.get("token", "")),
                username=str(data.get("username", "")),
            )
        except Exception:
            return cls()

    def save(self) -> None:
        p = _auth_file()
        payload = {"base_url": _normalize_base_url(self.base_url), "token": self.token, "username": self.username}
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class CloudClient:
    def __init__(self, auth: Optional[CloudAuth] = None):
        self.auth = auth or CloudAuth.load()

    @property
    def base_url(self) -> str:
        return _normalize_base_url(self.auth.base_url)

    def set_base_url(self, base_url: str) -> None:
        self.auth.base_url = _normalize_base_url(base_url)
        self.auth.save()

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def is_logged_in(self) -> bool:
        return bool(self.base_url and self.auth.token)

    def logout(self) -> None:
        self.auth.token = ""
        self.auth.username = ""
        self.auth.save()

    # -----------------
    # HTTP
    # -----------------
    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None, auth: bool = False) -> Dict[str, Any]:
        if not self.base_url:
            raise CloudError("서버 URL이 설정되지 않았습니다.")
        url = f"{self.base_url}{path}"

        headers = {"Accept": "application/json"}
        data_bytes: Optional[bytes] = None
        if body is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
            data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        if auth:
            if not self.auth.token:
                raise CloudError("로그인이 필요합니다.")
            headers["Authorization"] = f"Bearer {self.auth.token}"

        req = urllib.request.Request(url=url, method=method.upper(), headers=headers, data=data_bytes)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return json.loads(raw) if raw else {"ok": True}
                except Exception as e:
                    raise CloudError(f"서버 응답 파싱 실패: {e}") from e
        except urllib.error.HTTPError as e:
            raw = ""
            try:
                raw = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            try:
                payload = json.loads(raw) if raw else {}
            except Exception:
                payload = {}
            msg = payload.get("error") or payload.get("message") or raw or str(e)
            raise CloudError(f"HTTP {e.code}: {msg}")
        except urllib.error.URLError as e:
            raise CloudError(f"서버 연결 실패: {e}") from e

    # -----------------
    # Auth
    # -----------------
    def register(self, username: str, password: str) -> Dict[str, Any]:
        res = self._request("POST", "/auth/register", {"username": username, "password": password}, auth=False)
        if res.get("ok") and res.get("token"):
            self.auth.token = str(res.get("token"))
            self.auth.username = str((res.get("user") or {}).get("username") or username)
            self.auth.save()
        return res

    def login(self, username: str, password: str) -> Dict[str, Any]:
        res = self._request("POST", "/auth/login", {"username": username, "password": password}, auth=False)
        if res.get("ok") and res.get("token"):
            self.auth.token = str(res.get("token"))
            self.auth.username = str((res.get("user") or {}).get("username") or username)
            self.auth.save()
        return res

    def me(self) -> Dict[str, Any]:
        return self._request("GET", "/me", auth=True)

    # -----------------
    # Profile / stats
    # -----------------
    def upload_profile(self, total_score: int, rank: str) -> Dict[str, Any]:
        return self._request("PUT", "/me/profile", {"total_score": int(total_score), "rank": str(rank)}, auth=True)

    # -----------------
    # Presets
    # -----------------
    def list_presets(self) -> Dict[str, Any]:
        return self._request("GET", "/presets", auth=True)

    def get_preset(self, name: str) -> Dict[str, Any]:
        return self._request("GET", f"/presets/{urllib.parse.quote(name)}", auth=True)

    def put_preset(self, name: str, content: str) -> Dict[str, Any]:
        return self._request("PUT", f"/presets/{urllib.parse.quote(name)}", {"content": content}, auth=True)

    def delete_preset(self, name: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/presets/{urllib.parse.quote(name)}", auth=True)

    def sync_presets_dir(self, preset_dir: str) -> Tuple[int, int]:
        """
        로컬 preset_dir의 *.txt를 서버로 업로드하고,
        서버에만 있는 프리셋은 로컬로 다운로드합니다.

        반환: (업로드 수, 다운로드 수)
        """
        if not self.is_logged_in():
            raise CloudError("로그인이 필요합니다.")

        pdir = Path(preset_dir).expanduser()
        pdir.mkdir(parents=True, exist_ok=True)

        uploaded = 0
        downloaded = 0

        # 1) 로컬 -> 서버 업로드
        for f in sorted(pdir.glob("*.txt")):
            try:
                content = f.read_text(encoding="utf-8")
            except Exception:
                continue
            name = f.stem
            self.put_preset(name, content)
            uploaded += 1

        # 2) 서버 -> 로컬 다운로드 (로컬에 없으면 저장)
        res = self.list_presets()
        presets = res.get("presets") or []
        for item in presets:
            try:
                name = str(item.get("name") or "").strip()
            except Exception:
                continue
            if not name:
                continue
            local_path = pdir / f"{name}.txt"
            if local_path.exists():
                continue
            got = self._request("GET", f"/presets/{urllib.parse.quote(name)}", auth=True)
            preset = got.get("preset") or {}
            content = str(preset.get("content") or "")
            try:
                local_path.write_text(content, encoding="utf-8")
                downloaded += 1
            except Exception:
                pass

        return uploaded, downloaded

