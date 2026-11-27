"""Official Starter Mod Backend for Aether Nebula (Schema v1).

Demonstrates:
- Standard ``create_mod(context)`` entry point and ``handle_action(action, payload)`` dispatcher
- Encrypted Vault-only SQLite storage under ``{vault_root}/mods/{mod_id}/notes.db``
- Clean lifecycle hooks: ``on_vault_open``, ``on_vault_close``, and ``on_backup``
- Externalized main-table columns via ``get_profile_columns(profile_ids)``
- Externalized row action (``quick_stamp_profile``) and toolbar action (``batch_refresh_tags``)

Runtime dependency boundary:
Stick to Python's standard library plus host-bundled ``httpx`` / ``yaml`` so this Mod
runs identically in source mode and frozen builds (``Nebula.exe`` / ``.app`` / Linux).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import threading
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TemplateMod:
    """Reference Nebula Mod instance returned by :func:`create_mod`."""

    def __init__(self, context: Any) -> None:
        self._ctx = context
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle Hooks (invoked automatically by ModManager)
    # ------------------------------------------------------------------

    def on_vault_open(self, data_dir: Path | None) -> None:
        """Open Vault-isolated SQLite database when the encrypted Vault mounts."""
        with self._lock:
            self.on_vault_close()
            if data_dir is not None:
                self._open_db(Path(data_dir) / "notes.db")

    def on_vault_close(self) -> None:
        """Release all DB/file handles before Vault unmount, reload, or safe shutdown."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                finally:
                    self._conn = None

    def on_backup(self, backup_dir: Path) -> list[str]:
        """Snapshot the Mod's Vault SQLite DB when the user triggers Vault Backup."""
        with self._lock:
            if self._conn is None:
                return []
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = Path(backup_dir) / f"{self._ctx.mod_id}_backup_{ts}.db"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dst_conn = sqlite3.connect(str(dest))
            try:
                self._conn.backup(dst_conn)
            finally:
                dst_conn.close()
            return [str(dest)]

    # ------------------------------------------------------------------
    # SQLite Vault Helper (never writes outside context.get_data_dir())
    # ------------------------------------------------------------------

    def _open_db(self, db_path: Path) -> sqlite3.Connection:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_tags (
                profile_id INTEGER PRIMARY KEY,
                tag TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                stamp_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        self._conn = conn
        return conn

    def _ensure_db(self) -> sqlite3.Connection:
        with self._lock:
            if self._conn is None:
                data_dir = self._ctx.get_data_dir()
                return self._open_db(Path(data_dir) / "notes.db")
            return self._conn

    def _fetch_tags_map(self, profile_ids: list[int] | None = None) -> dict[int, dict[str, Any]]:
        conn = self._ensure_db()
        if profile_ids is not None:
            clean_ids = [int(x) for x in profile_ids]
            if not clean_ids:
                return {}
            placeholders = ",".join("?" for _ in clean_ids)
            rows = conn.execute(
                f"SELECT profile_id, tag, note, stamp_count, updated_at "
                f"FROM profile_tags WHERE profile_id IN ({placeholders})",
                clean_ids,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT profile_id, tag, note, stamp_count, updated_at "
                "FROM profile_tags ORDER BY updated_at DESC"
            ).fetchall()
        return {int(r["profile_id"]): dict(r) for r in rows}

    # ------------------------------------------------------------------
    # Externalized Main-Table Column Provider
    # ------------------------------------------------------------------

    def get_profile_columns(self, profile_ids: list[int]) -> dict[str, dict[str, Any]]:
        """Return cells for ``ui.profile_table_columns`` keyed by ``str(profile_id)``."""
        if not self._ctx.is_vault_mounted():
            return {}
        clean_ids = [int(pid) for pid in (profile_ids or [])]
        if not clean_ids:
            return {}

        tags_map = self._fetch_tags_map(clean_ids)
        result: dict[str, dict[str, Any]] = {}
        for pid in clean_ids:
            row = tags_map.get(pid)
            if not row or (not row["tag"] and not row["note"] and not row["stamp_count"]):
                result[str(pid)] = {
                    "mod_tag": {
                        "text": "未标记",
                        "subtext": "",
                        "badge": "",
                        "tone": "muted",
                        "title": "点击「示例」或「打卡」为该环境添加加密盘扩展标签",
                    }
                }
                continue

            tag = str(row["tag"] or "").strip()
            note = str(row["note"] or "").strip()
            stamps = int(row["stamp_count"] or 0)
            result[str(pid)] = {
                "mod_tag": {
                    "text": tag or "已打卡",
                    "subtext": note[:28] if note else f"更新于 {str(row['updated_at'])[:10]}",
                    "badge": f"×{stamps}" if stamps > 0 else "已标记",
                    "tone": "emerald" if stamps > 0 else "sky",
                    "title": f"标签: {tag or '-'}\n备注: {note or '-'}\n打卡次数: {stamps}\n更新时间: {row['updated_at']}",
                }
            }
        return result

    # ------------------------------------------------------------------
    # Action Dispatcher (called via PyWebView IPC bridge.invoke)
    # ------------------------------------------------------------------

    def handle_action(self, action: str, payload: dict[str, Any]) -> Any:
        handlers = {
            "get_overview": self._act_get_overview,
            "get_profile_columns": self._act_get_profile_columns,
            "save_tag": self._act_save_tag,
            "delete_tag": self._act_delete_tag,
            "quick_stamp_profile": self._act_quick_stamp_profile,
            "batch_refresh_tags": self._act_batch_refresh_tags,
        }
        fn = handlers.get(action)
        if fn is None:
            raise ValueError(f"未知的 {self._ctx.mod_id} Mod 操作: {action!r}")
        return fn(payload)

    def _act_get_overview(self, _payload: dict[str, Any]) -> dict[str, Any]:
        profiles = self._ctx.list_profiles()
        tags_map = self._fetch_tags_map()
        compact_profiles = [
            {
                "id": int(p["id"]),
                "code": str(p.get("code") or ""),
                "name": str(p.get("name") or ""),
                "node_name": str(p.get("node_name") or ""),
                "is_running": bool(p.get("is_running")),
            }
            for p in profiles
        ]
        return {
            "mod_id": self._ctx.mod_id,
            "app_version": self._ctx.app_version,
            "host_os": self._ctx.host_os,
            "profiles": compact_profiles,
            "tags": list(tags_map.values()),
        }

    def _act_get_profile_columns(self, payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        raw_ids = payload.get("profile_ids")
        ids = [int(x) for x in raw_ids] if isinstance(raw_ids, list) else []
        return self.get_profile_columns(ids)

    def _act_save_tag(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_pid = payload.get("profile_id")
        if raw_pid in (None, ""):
            raise ValueError("请选择一个目标 Nebula 指纹环境")
        profile_id = int(raw_pid)
        if self._ctx.get_profile(profile_id) is None:
            raise ValueError(f"环境不存在: id={profile_id}")

        tag = str(payload.get("tag") or "").strip()[:32]
        note = str(payload.get("note") or "").strip()[:240]
        if not tag and not note:
            raise ValueError("标签与备注不能同时为空")

        now = _utc_now_iso()
        conn = self._ensure_db()
        with self._lock:
            existing = conn.execute(
                "SELECT stamp_count FROM profile_tags WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            stamps = int(existing["stamp_count"]) if existing else 0
            conn.execute(
                """
                INSERT INTO profile_tags (profile_id, tag, note, stamp_count, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    tag = excluded.tag,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (profile_id, tag, note, stamps, now),
            )
            conn.commit()
        return {
            "saved": True,
            "item": {
                "profile_id": profile_id,
                "tag": tag,
                "note": note,
                "stamp_count": stamps,
                "updated_at": now,
            },
        }

    def _act_delete_tag(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_pid = payload.get("profile_id")
        if raw_pid in (None, ""):
            raise ValueError("缺少 profile_id")
        profile_id = int(raw_pid)
        conn = self._ensure_db()
        with self._lock:
            conn.execute("DELETE FROM profile_tags WHERE profile_id = ?", (profile_id,))
            conn.commit()
        return {"deleted": True, "profile_id": profile_id}

    def _act_quick_stamp_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Externalized row action handler declared in ``ui.profile_row_actions``."""
        raw_pid = payload.get("profile_id")
        if raw_pid in (None, ""):
            raise ValueError("缺少 profile_id")
        profile_id = int(raw_pid)
        prof = self._ctx.get_profile(profile_id)
        if prof is None:
            raise ValueError(f"环境不存在: id={profile_id}")

        now = _utc_now_iso()
        conn = self._ensure_db()
        with self._lock:
            existing = conn.execute(
                "SELECT tag, note, stamp_count FROM profile_tags WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            tag = str(existing["tag"]) if existing and existing["tag"] else "已打卡"
            note = str(existing["note"]) if existing else ""
            stamps = (int(existing["stamp_count"]) if existing else 0) + 1
            conn.execute(
                """
                INSERT INTO profile_tags (profile_id, tag, note, stamp_count, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    tag = excluded.tag,
                    stamp_count = excluded.stamp_count,
                    updated_at = excluded.updated_at
                """,
                (profile_id, tag, note, stamps, now),
            )
            conn.commit()
        code = str(prof.get("code") or f"#{profile_id}")
        return {
            "ok": True,
            "profile_id": profile_id,
            "stamp_count": stamps,
            "message": f"[{code}] 已记录打卡（累计 {stamps} 次）",
        }

    def _act_batch_refresh_tags(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Externalized toolbar action handler declared in ``ui.toolbar_actions``."""
        raw_ids = payload.get("profile_ids")
        filter_ids = [int(x) for x in raw_ids] if isinstance(raw_ids, list) and raw_ids else None
        tags_map = self._fetch_tags_map(filter_ids)
        total_stamps = sum(int(item.get("stamp_count") or 0) for item in tags_map.values())
        return {
            "ok": True,
            "tagged_profiles": len(tags_map),
            "total_stamps": total_stamps,
            "message": f"已同步 {len(tags_map)} 个环境的扩展标签（累计打卡 {total_stamps} 次）",
        }


def create_mod(context: Any) -> TemplateMod:
    """Entry point discovered by Nebula's :class:`ModManager`."""
    return TemplateMod(context)
