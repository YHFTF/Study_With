"""
Study With - Cloud Server (Flask)

Oracle ARM 같은 외부 서버에 배포하여 다음 데이터를 저장/동기화합니다.
- 로그인(회원가입/로그인) + 토큰 인증
- 프리셋 데이터(.txt 내용)
- 유저 레벨/통계 데이터(점수/등급 등)

의도적으로 의존성을 늘리지 않기 위해 Flask 기본 구성요소(werkzeug, itsdangerous)와
표준 라이브러리(sqlite3)만 사용합니다.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

from flask import Flask, Response, g, jsonify, request
from flask_cors import CORS
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _get_db_path() -> str:
    return os.getenv("STUDY_WITH_SERVER_DB", "study_with.db")


def _get_secret_key() -> str:
    secret = os.getenv("STUDY_WITH_SERVER_SECRET")
    if not secret:
        # 개발 편의 기본값 (운영에서는 반드시 환경변수로 지정 권장)
        secret = "dev-insecure-secret-change-me"
    return secret


def _token_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_get_secret_key(), salt="study-with-auth")


def _make_token(user_id: int) -> str:
    payload = {"uid": user_id}
    return _token_serializer().dumps(payload)


def _verify_token(token: str, max_age_seconds: int) -> int:
    data = _token_serializer().loads(token, max_age=max_age_seconds)
    uid = data.get("uid")
    if not isinstance(uid, int):
        raise BadSignature("invalid uid type")
    return uid


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _get_conn() -> sqlite3.Connection:
    conn = getattr(g, "_db_conn", None)
    if conn is None:
        conn = _conn()
        g._db_conn = conn
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_profile (
            user_id INTEGER PRIMARY KEY,
            level INTEGER NOT NULL DEFAULT 1,
            xp INTEGER NOT NULL DEFAULT 0,
            total_score INTEGER NOT NULL DEFAULT 0,
            rank TEXT NOT NULL DEFAULT 'BRONZE',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, name),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def _json_error(message: str, status: int = 400) -> Tuple[Response, int]:
    return jsonify({"ok": False, "error": message}), status


def _require_json(required_fields: Tuple[str, ...]) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Response, int]]]:
    if not request.is_json:
        return None, _json_error("JSON body required", 415)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, _json_error("Invalid JSON body", 400)
    for f in required_fields:
        if f not in data:
            return None, _json_error(f"Missing field: {f}", 400)
    return data, None


def _auth_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return _json_error("Missing Bearer token", 401)
        token = auth.removeprefix("Bearer ").strip()
        if not token:
            return _json_error("Missing Bearer token", 401)

        try:
            uid = _verify_token(token, max_age_seconds=60 * 60 * 24 * 30)  # 30일
        except SignatureExpired:
            return _json_error("Token expired", 401)
        except BadSignature:
            return _json_error("Invalid token", 401)

        g.user_id = uid
        return fn(*args, **kwargs)

    return wrapper


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    CORS(app)

    # DB schema init (앱 시작 시 1회)
    conn = _conn()
    try:
        _init_schema(conn)
    finally:
        conn.close()

    @app.teardown_appcontext
    def _close_db(_exc: Optional[BaseException]) -> None:
        conn2 = getattr(g, "_db_conn", None)
        if conn2 is not None:
            try:
                conn2.close()
            except Exception:
                pass

    @app.get("/health")
    def health() -> Any:
        return jsonify({"ok": True, "time": _utc_now_iso()})

    # -----------------------
    # Auth
    # -----------------------
    @app.post("/auth/register")
    def register() -> Any:
        data, err = _require_json(("username", "password"))
        if err:
            return err
        username = str(data["username"]).strip()
        password = str(data["password"])
        if len(username) < 3:
            return _json_error("username must be at least 3 chars", 400)
        if len(password) < 6:
            return _json_error("password must be at least 6 chars", 400)

        conn3 = _get_conn()
        try:
            cur = conn3.execute(
                "INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), _utc_now_iso()),
            )
            user_id = int(cur.lastrowid)
            conn3.execute(
                "INSERT OR IGNORE INTO user_profile(user_id, level, xp, total_score, rank, updated_at) VALUES (?, 1, 0, 0, 'BRONZE', ?)",
                (user_id, _utc_now_iso()),
            )
            conn3.commit()
        except sqlite3.IntegrityError:
            return _json_error("username already exists", 409)

        token = _make_token(user_id)
        return jsonify({"ok": True, "token": token, "user": {"id": user_id, "username": username}})

    @app.post("/auth/login")
    def login() -> Any:
        data, err = _require_json(("username", "password"))
        if err:
            return err
        username = str(data["username"]).strip()
        password = str(data["password"])

        conn3 = _get_conn()
        row = conn3.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            return _json_error("invalid credentials", 401)
        if not check_password_hash(row["password_hash"], password):
            return _json_error("invalid credentials", 401)

        token = _make_token(int(row["id"]))
        return jsonify({"ok": True, "token": token, "user": {"id": int(row["id"]), "username": username}})

    # -----------------------
    # User profile / stats
    # -----------------------
    @app.get("/me")
    @_auth_required
    def me() -> Any:
        uid = int(g.user_id)
        conn3 = _get_conn()
        user = conn3.execute("SELECT id, username, created_at FROM users WHERE id = ?", (uid,)).fetchone()
        if not user:
            return _json_error("user not found", 404)
        profile = conn3.execute(
            "SELECT level, xp, total_score, rank, updated_at FROM user_profile WHERE user_id = ?",
            (uid,),
        ).fetchone()
        if not profile:
            # 보정
            conn3.execute(
                "INSERT OR IGNORE INTO user_profile(user_id, level, xp, total_score, rank, updated_at) VALUES (?, 1, 0, 0, 'BRONZE', ?)",
                (uid, _utc_now_iso()),
            )
            conn3.commit()
            profile = conn3.execute(
                "SELECT level, xp, total_score, rank, updated_at FROM user_profile WHERE user_id = ?",
                (uid,),
            ).fetchone()

        return jsonify(
            {
                "ok": True,
                "user": {"id": int(user["id"]), "username": user["username"], "created_at": user["created_at"]},
                "profile": {
                    "level": int(profile["level"]),
                    "xp": int(profile["xp"]),
                    "total_score": int(profile["total_score"]),
                    "rank": profile["rank"],
                    "updated_at": profile["updated_at"],
                },
            }
        )

    @app.put("/me/profile")
    @_auth_required
    def update_profile() -> Any:
        """
        클라이언트가 계산한 통계/등급을 서버에 업로드합니다.
        (레벨/xp는 간단 규칙으로 서버에서 계산)
        """
        data, err = _require_json(("total_score", "rank"))
        if err:
            return err
        try:
            total_score = int(data["total_score"])
        except Exception:
            return _json_error("total_score must be int", 400)
        rank = str(data["rank"]).strip().upper()
        if not rank:
            rank = "BRONZE"

        # 간단 레벨/XP 규칙: 100점당 레벨 1 증가
        level = max(1, total_score // 100 + 1)
        xp = max(0, total_score % 100)

        uid = int(g.user_id)
        conn3 = _get_conn()
        conn3.execute(
            """
            INSERT INTO user_profile(user_id, level, xp, total_score, rank, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                level=excluded.level,
                xp=excluded.xp,
                total_score=excluded.total_score,
                rank=excluded.rank,
                updated_at=excluded.updated_at
            """,
            (uid, level, xp, total_score, rank, _utc_now_iso()),
        )
        conn3.commit()
        return jsonify({"ok": True, "profile": {"level": level, "xp": xp, "total_score": total_score, "rank": rank}})

    # -----------------------
    # Presets
    # -----------------------
    @app.get("/presets")
    @_auth_required
    def list_presets() -> Any:
        uid = int(g.user_id)
        conn3 = _get_conn()
        rows = conn3.execute(
            "SELECT name, updated_at, length(content) AS size FROM presets WHERE user_id = ? ORDER BY name ASC",
            (uid,),
        ).fetchall()
        items = [{"name": r["name"], "updated_at": r["updated_at"], "size": int(r["size"] or 0)} for r in rows]
        return jsonify({"ok": True, "presets": items})

    @app.get("/presets/<string:name>")
    @_auth_required
    def get_preset(name: str) -> Any:
        uid = int(g.user_id)
        conn3 = _get_conn()
        row = conn3.execute(
            "SELECT name, content, updated_at FROM presets WHERE user_id = ? AND name = ?",
            (uid, name),
        ).fetchone()
        if not row:
            return _json_error("preset not found", 404)
        return jsonify({"ok": True, "preset": {"name": row["name"], "content": row["content"], "updated_at": row["updated_at"]}})

    @app.put("/presets/<string:name>")
    @_auth_required
    def upsert_preset(name: str) -> Any:
        data, err = _require_json(("content",))
        if err:
            return err
        content = str(data["content"])
        uid = int(g.user_id)
        now = _utc_now_iso()
        conn3 = _get_conn()
        conn3.execute(
            """
            INSERT INTO presets(user_id, name, content, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, name) DO UPDATE SET
                content=excluded.content,
                updated_at=excluded.updated_at
            """,
            (uid, name, content, now),
        )
        conn3.commit()
        return jsonify({"ok": True, "preset": {"name": name, "updated_at": now}})

    @app.delete("/presets/<string:name>")
    @_auth_required
    def delete_preset(name: str) -> Any:
        uid = int(g.user_id)
        conn3 = _get_conn()
        cur = conn3.execute("DELETE FROM presets WHERE user_id = ? AND name = ?", (uid, name))
        conn3.commit()
        if cur.rowcount == 0:
            return _json_error("preset not found", 404)
        return jsonify({"ok": True})

    return app


def main() -> None:
    """
    로컬 실행 예:
      STUDY_WITH_SERVER_SECRET="..." python -m study_with.cloud_server
    """
    host = os.getenv("STUDY_WITH_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("STUDY_WITH_SERVER_PORT", "8000"))
    debug = os.getenv("STUDY_WITH_SERVER_DEBUG", "").lower() in ("1", "true", "yes")
    app = create_app()
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    main()

