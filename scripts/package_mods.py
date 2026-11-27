#!/usr/bin/env python3
"""Validate and package Aether Nebula Mods into reproducible ZIP archives.

Produces:
  - ``<output_dir>/nebula-mod-<id>-v<version>.zip`` (with ``<id>/...`` top-level folder)
  - ``<output_dir>/SHA256SUMS.txt``

Strictly enforces Nebula Mod Schema v1 manifests, offline UI asset hygiene (zero
``http://`` / ``https://`` URLs in ``panel.html`` / ``panel.css``), path-traversal
boundaries, and excludes ``_template``, ``__pycache__``, ``*.pyc``, ``*.db``, ``*.log``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
import zipfile

MOD_SCHEMA_VERSION = 1
MOD_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+.][0-9A-Za-z.-]+)?$")
URL_RE = re.compile(r"https?://", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

ALLOWED_PLATFORMS: frozenset[str] = frozenset({"windows", "macos", "linux"})
ALLOWED_PERMISSIONS: frozenset[str] = frozenset(
    {
        "vault_storage",
        "profiles_read",
        "profiles_write",
        "browser_cdp",
        "proxy_http",
    }
)
ALLOWED_MOUNT_POINTS: frozenset[str] = frozenset(
    {"topbar", "profile_row", "toolbar", "inline_panel"}
)
ALLOWED_ACTION_STYLES: frozenset[str] = frozenset(
    {"default", "primary", "emerald", "sky", "amber", "danger"}
)
ALLOWED_STORE_CATEGORIES: frozenset[str] = frozenset(
    {
        "account-automation",
        "quota-billing",
        "proxy-network",
        "workspace-ui",
        "automation-cdp",
        "security-audit",
    }
)
ALLOWED_STORE_UI_SLOTS: frozenset[str] = frozenset(
    {
        "topbar",
        "profile_row",
        "profile_table_columns",
        "profile_row_actions",
        "toolbar",
        "toolbar_actions",
        "inline_panel",
    }
)

EXCLUDED_DIRS: frozenset[str] = frozenset(
    {"__pycache__", ".pytest_cache", ".git", ".venv", "node_modules"}
)
EXCLUDED_SUFFIXES: tuple[str, ...] = (
    ".pyc",
    ".pyo",
    ".db",
    ".db-wal",
    ".db-shm",
    ".sqlite",
    ".sqlite3",
    ".log",
)
EXCLUDED_NAMES: frozenset[str] = frozenset({".DS_Store", "Thumbs.db"})
FIXED_ZIP_DATE = (2026, 1, 1, 0, 0, 0)


class ManifestValidationError(ValueError):
    """Raised when a Mod manifest or registry entry fails strict validation."""


def _safe_rel_path(mod_dir: Path, rel_path: str, *, field_name: str) -> Path:
    cleaned = str(rel_path or "").strip()
    if not cleaned or cleaned.startswith(("/", "\\")) or ":" in cleaned:
        raise ManifestValidationError(f"{field_name} has invalid relative path: {rel_path!r}")
    root = mod_dir.resolve()
    candidate = (root / cleaned).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ManifestValidationError(f"{field_name} escapes mod directory: {rel_path!r}") from exc
    return candidate


def validate_mod_dir(mod_dir: Path, *, enforce_folder_match: bool = True) -> dict[str, Any]:
    """Strictly validate a Mod folder and its ``mod.json`` manifest."""
    manifest_path = mod_dir / "mod.json"
    if not manifest_path.is_file():
        raise ManifestValidationError(f"Missing mod.json in {mod_dir}")

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"Invalid JSON in {manifest_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ManifestValidationError(f"{manifest_path}: root must be a JSON object")

    if raw.get("schema_version") != MOD_SCHEMA_VERSION:
        raise ManifestValidationError(
            f"{manifest_path}: schema_version must be {MOD_SCHEMA_VERSION}, got {raw.get('schema_version')!r}"
        )

    mod_id = str(raw.get("id") or "").strip()
    if not MOD_ID_RE.match(mod_id):
        raise ManifestValidationError(
            f"{manifest_path}: invalid id {mod_id!r} (must match {MOD_ID_RE.pattern})"
        )
    if enforce_folder_match and mod_id != mod_dir.name:
        raise ManifestValidationError(
            f"{manifest_path}: folder name {mod_dir.name!r} does not match manifest id {mod_id!r}"
        )

    name = str(raw.get("name") or "").strip()
    if not name:
        raise ManifestValidationError(f"{manifest_path}: missing required 'name'")

    version = str(raw.get("version") or "").strip()
    if not SEMVER_RE.match(version):
        raise ManifestValidationError(
            f"{manifest_path}: invalid semantic version {version!r}"
        )

    platforms = raw.get("platforms", ["windows", "macos", "linux"])
    if not isinstance(platforms, list) or not platforms:
        raise ManifestValidationError(f"{manifest_path}: 'platforms' must be a non-empty array")
    for plat in platforms:
        if not isinstance(plat, str) or plat.lower() not in ALLOWED_PLATFORMS:
            raise ManifestValidationError(f"{manifest_path}: unsupported platform {plat!r}")

    permissions = raw.get("permissions", [])
    if not isinstance(permissions, list):
        raise ManifestValidationError(f"{manifest_path}: 'permissions' must be an array")
    for perm in permissions:
        if not isinstance(perm, str) or perm not in ALLOWED_PERMISSIONS:
            raise ManifestValidationError(f"{manifest_path}: unknown permission {perm!r}")

    backend_rel = str(raw.get("backend") or "backend.py").strip()
    backend_path = _safe_rel_path(mod_dir, backend_rel, field_name="backend")
    if not backend_path.is_file():
        raise ManifestValidationError(f"{manifest_path}: backend file not found: {backend_rel}")

    ui = raw.get("ui")
    if ui is not None:
        if not isinstance(ui, dict):
            raise ManifestValidationError(f"{manifest_path}: 'ui' must be an object")

        mount_points = ui.get("mount_points", [])
        if not isinstance(mount_points, list):
            raise ManifestValidationError(f"{manifest_path}: 'ui.mount_points' must be an array")
        for mp in mount_points:
            if not isinstance(mp, str) or mp not in ALLOWED_MOUNT_POINTS:
                raise ManifestValidationError(f"{manifest_path}: unknown mount_point {mp!r}")

        for key in ("entry", "script", "style"):
            rel = str(ui.get(key) or "").strip()
            if not rel:
                continue
            asset_path = _safe_rel_path(mod_dir, rel, field_name=f"ui.{key}")
            if not asset_path.is_file():
                raise ManifestValidationError(f"{manifest_path}: ui.{key} file missing: {rel}")
            if key in ("entry", "style"):
                content = asset_path.read_text(encoding="utf-8")
                if URL_RE.search(content):
                    raise ManifestValidationError(
                        f"{asset_path}: external http(s):// URL is forbidden in Mod UI assets"
                    )

        for action_slot in ("profile_row_actions", "toolbar_actions"):
            items = ui.get(action_slot)
            if items is None:
                continue
            if not isinstance(items, list):
                raise ManifestValidationError(f"{manifest_path}: ui.{action_slot} must be an array")
            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    raise ManifestValidationError(f"{manifest_path}: ui.{action_slot}[{idx}] must be an object")
                if not str(item.get("label") or "").strip() or not str(item.get("action") or "").strip():
                    raise ManifestValidationError(
                        f"{manifest_path}: ui.{action_slot}[{idx}] requires non-empty 'label' and 'action'"
                    )
                style = str(item.get("style") or "default").strip().lower()
                if style not in ALLOWED_ACTION_STYLES:
                    raise ManifestValidationError(
                        f"{manifest_path}: ui.{action_slot}[{idx}] invalid style {style!r}"
                    )

        cols = ui.get("profile_table_columns")
        if cols is not None:
            if not isinstance(cols, list):
                raise ManifestValidationError(f"{manifest_path}: ui.profile_table_columns must be an array")
            for idx, col in enumerate(cols):
                if not isinstance(col, dict):
                    raise ManifestValidationError(
                        f"{manifest_path}: ui.profile_table_columns[{idx}] must be an object"
                    )
                if not str(col.get("id") or "").strip() or not str(col.get("label") or "").strip():
                    raise ManifestValidationError(
                        f"{manifest_path}: ui.profile_table_columns[{idx}] requires non-empty 'id' and 'label'"
                    )

    return raw


def validate_registry(registry_path: Path, mods_dir: Path | None = None) -> dict[str, Any]:
    """Validate ``registry/mods.json`` schema and cross-check bundled Mods."""
    if not registry_path.is_file():
        raise ManifestValidationError(f"Registry file not found: {registry_path}")
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"Invalid JSON in {registry_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestValidationError(f"{registry_path}: root must be an object")
    if data.get("schema_version") != 1:
        raise ManifestValidationError(f"{registry_path}: schema_version must be 1")
    mods = data.get("mods")
    if not isinstance(mods, list) or not mods:
        raise ManifestValidationError(f"{registry_path}: 'mods' must be a non-empty array")

    required_fields = (
        "id",
        "name",
        "version",
        "author",
        "description",
        "platforms",
        "permissions",
        "min_nebula_version",
        "download_url",
        "sha256",
        "homepage",
    )
    seen_ids: set[str] = set()
    for idx, entry in enumerate(mods):
        if not isinstance(entry, dict):
            raise ManifestValidationError(f"{registry_path}: mods[{idx}] must be an object")
        for field in required_fields:
            if field not in entry:
                raise ManifestValidationError(f"{registry_path}: mods[{idx}] missing field {field!r}")
        mod_id = str(entry["id"]).strip()
        if not MOD_ID_RE.match(mod_id):
            raise ManifestValidationError(f"{registry_path}: mods[{idx}] invalid id {mod_id!r}")
        if mod_id in seen_ids:
            raise ManifestValidationError(f"{registry_path}: duplicate mod id {mod_id!r}")
        seen_ids.add(mod_id)

        if not SEMVER_RE.match(str(entry["version"])):
            raise ManifestValidationError(f"{registry_path}: mods[{idx}] invalid version {entry['version']!r}")
        if not SEMVER_RE.match(str(entry["min_nebula_version"])):
            raise ManifestValidationError(
                f"{registry_path}: mods[{idx}] invalid min_nebula_version {entry['min_nebula_version']!r}"
            )

        platforms = entry["platforms"]
        if not isinstance(platforms, list) or not platforms or any(p not in ALLOWED_PLATFORMS for p in platforms):
            raise ManifestValidationError(f"{registry_path}: mods[{idx}] invalid platforms {platforms!r}")

        perms = entry["permissions"]
        if not isinstance(perms, list) or any(p not in ALLOWED_PERMISSIONS for p in perms):
            raise ManifestValidationError(f"{registry_path}: mods[{idx}] invalid permissions {perms!r}")

        sha = str(entry["sha256"]).strip()
        if sha and not SHA256_RE.match(sha):
            raise ManifestValidationError(f"{registry_path}: mods[{idx}] sha256 must be 64 lowercase hex chars")

        for url_field in ("download_url", "homepage"):
            val = str(entry[url_field]).strip()
            if not val.startswith("https://"):
                raise ManifestValidationError(
                    f"{registry_path}: mods[{idx}] {url_field} must start with https://"
                )

        if mods_dir is not None and entry.get("bundled") and (mods_dir / mod_id).is_dir():
            local_manifest_path = mods_dir / mod_id / "mod.json"
            if not local_manifest_path.is_file():
                raise ManifestValidationError(
                    f"{registry_path}: bundled mod {mod_id!r} not found at {local_manifest_path}"
                )
            local_manifest = json.loads(local_manifest_path.read_text(encoding="utf-8"))
            if str(local_manifest.get("version")) != str(entry["version"]):
                raise ManifestValidationError(
                    f"{registry_path}: bundled mod {mod_id!r} version {entry['version']!r} "
                    f"does not match {local_manifest_path} ({local_manifest.get('version')!r})"
                )

    return data


def _validate_store_entry(
    entry: Any,
    *,
    source_label: str,
    mods_dir: Path | None = None,
    expected_id: str | None = None,
) -> str:
    if not isinstance(entry, dict):
        raise ManifestValidationError(f"{source_label}: entry must be an object")
    required_fields = (
        "id",
        "name",
        "version",
        "author",
        "description",
        "category",
        "platforms",
        "permissions",
        "min_nebula_version",
        "download_url",
        "sha256",
        "homepage",
    )
    for field in required_fields:
        if field not in entry:
            raise ManifestValidationError(f"{source_label}: missing field {field!r}")

    mod_id = str(entry["id"]).strip()
    if not MOD_ID_RE.match(mod_id):
        raise ManifestValidationError(f"{source_label}: invalid id {mod_id!r}")
    if expected_id is not None and mod_id != expected_id:
        raise ManifestValidationError(
            f"{source_label}: filename id {expected_id!r} does not match entry id {mod_id!r}"
        )
    if not SEMVER_RE.match(str(entry["version"])):
        raise ManifestValidationError(f"{source_label}: invalid version {entry['version']!r}")
    if not SEMVER_RE.match(str(entry["min_nebula_version"])):
        raise ManifestValidationError(
            f"{source_label}: invalid min_nebula_version {entry['min_nebula_version']!r}"
        )
    if str(entry["category"]) not in ALLOWED_STORE_CATEGORIES:
        raise ManifestValidationError(f"{source_label}: invalid category {entry['category']!r}")

    platforms = entry["platforms"]
    if not isinstance(platforms, list) or not platforms or any(p not in ALLOWED_PLATFORMS for p in platforms):
        raise ManifestValidationError(f"{source_label}: invalid platforms {platforms!r}")

    perms = entry["permissions"]
    if not isinstance(perms, list) or any(p not in ALLOWED_PERMISSIONS for p in perms):
        raise ManifestValidationError(f"{source_label}: invalid permissions {perms!r}")

    ui_slots = entry.get("ui_slots", [])
    if not isinstance(ui_slots, list) or any(s not in ALLOWED_STORE_UI_SLOTS for s in ui_slots):
        raise ManifestValidationError(f"{source_label}: invalid ui_slots {ui_slots!r}")

    sha = str(entry["sha256"]).strip()
    if sha and not SHA256_RE.match(sha):
        raise ManifestValidationError(f"{source_label}: sha256 must be 64 lowercase hex chars")

    for url_field in ("download_url", "homepage", "source_url"):
        if url_field in entry and entry[url_field]:
            val = str(entry[url_field]).strip()
            if not val.startswith("https://"):
                raise ManifestValidationError(f"{source_label}: {url_field} must start with https://")

    if mods_dir is not None and entry.get("bundled") and (mods_dir / mod_id).is_dir():
        local_manifest_path = mods_dir / mod_id / "mod.json"
        if not local_manifest_path.is_file():
            raise ManifestValidationError(
                f"{source_label}: bundled mod {mod_id!r} not found at {local_manifest_path}"
            )
        local_manifest = json.loads(local_manifest_path.read_text(encoding="utf-8"))
        if str(local_manifest.get("version")) != str(entry["version"]):
            raise ManifestValidationError(
                f"{source_label}: bundled mod {mod_id!r} version {entry['version']!r} "
                f"does not match {local_manifest_path} ({local_manifest.get('version')!r})"
            )

    return mod_id


def validate_store_catalog(catalog_path: Path, mods_dir: Path | None = None) -> dict[str, Any]:
    """Validate ``mod-store/catalog.json`` schema and cross-check bundled Mods."""
    if not catalog_path.is_file():
        raise ManifestValidationError(f"Store catalog file not found: {catalog_path}")
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"Invalid JSON in {catalog_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestValidationError(f"{catalog_path}: root must be an object")
    if data.get("schema_version") != 1:
        raise ManifestValidationError(f"{catalog_path}: schema_version must be 1")
    if not str(data.get("store_name") or "").strip():
        raise ManifestValidationError(f"{catalog_path}: missing store_name")
    if not SEMVER_RE.match(str(data.get("min_client_version") or "")):
        raise ManifestValidationError(f"{catalog_path}: invalid min_client_version")

    mods = data.get("mods")
    if not isinstance(mods, list) or not mods:
        raise ManifestValidationError(f"{catalog_path}: 'mods' must be a non-empty array")

    seen_ids: set[str] = set()
    for idx, entry in enumerate(mods):
        mod_id = _validate_store_entry(entry, source_label=f"{catalog_path}: mods[{idx}]", mods_dir=mods_dir)
        if mod_id in seen_ids:
            raise ManifestValidationError(f"{catalog_path}: duplicate mod id {mod_id!r}")
        seen_ids.add(mod_id)

    for fid in data.get("featured_ids", []):
        if fid not in seen_ids:
            raise ManifestValidationError(f"{catalog_path}: featured_ids references unknown mod {fid!r}")

    return data


def validate_store_submissions(submissions_dir: Path, mods_dir: Path | None = None) -> int:
    """Validate every ``<mod_id>.json`` under ``mod-store/submissions/``."""
    if not submissions_dir.is_dir():
        raise ManifestValidationError(f"Store submissions directory not found: {submissions_dir}")
    count = 0
    for path in sorted(submissions_dir.glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ManifestValidationError(f"Invalid JSON in {path}: {exc}") from exc
        _validate_store_entry(
            entry,
            source_label=str(path),
            mods_dir=mods_dir,
            expected_id=path.stem,
        )
        count += 1
    return count


def _should_exclude(rel_path: Path) -> bool:
    for part in rel_path.parts[:-1]:
        if part in EXCLUDED_DIRS:
            return True
    name = rel_path.name
    if name in EXCLUDED_NAMES or name.startswith("._"):
        return True
    if name.lower().endswith(EXCLUDED_SUFFIXES):
        return True
    return False


def _iter_package_files(mod_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(mod_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(mod_dir)
        if _should_exclude(rel):
            continue
        files.append(path)
    return files


def package_single_mod(mod_dir: Path, output_dir: Path) -> tuple[Path, str]:
    """Validate and package one Mod directory into a deterministic ZIP archive."""
    manifest = validate_mod_dir(mod_dir, enforce_folder_match=True)
    mod_id = str(manifest["id"]).strip()
    version = str(manifest["version"]).strip()

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"nebula-mod-{mod_id}-v{version}.zip"
    files = _iter_package_files(mod_dir)

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src in files:
            rel = src.relative_to(mod_dir).as_posix()
            arcname = f"{mod_id}/{rel}"
            info = zipfile.ZipInfo(filename=arcname, date_time=FIXED_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, src.read_bytes())

    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    return archive_path, digest


def discover_packable_mods(mods_dir: Path, selected: list[str] | None = None) -> list[Path]:
    if not mods_dir.is_dir():
        raise ManifestValidationError(f"Mods directory does not exist: {mods_dir}")

    selected_set = {m.strip() for m in (selected or []) if m.strip()}
    result: list[Path] = []
    for child in sorted(mods_dir.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name.startswith((".", "_")):
            continue
        if not (child / "mod.json").is_file():
            continue
        if selected_set and child.name not in selected_set:
            continue
        result.append(child)

    if selected_set:
        found = {p.name for p in result}
        missing = sorted(selected_set - found)
        if missing:
            raise ManifestValidationError(f"Requested Mod(s) not found under {mods_dir}: {', '.join(missing)}")
    return result


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Validate and package Aether Nebula Mods into ZIP archives + SHA256SUMS.txt."
    )
    parser.add_argument(
        "--mods-dir",
        type=Path,
        default=repo_root / "mods",
        help="Source directory containing Nebula Mods (default: mods)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root / "dist" / "mods",
        help="Output directory for built ZIP archives and SHA256SUMS.txt (default: dist/mods)",
    )
    parser.add_argument(
        "--mod",
        action="append",
        default=[],
        help="Specific Mod ID to package (repeatable; defaults to all non-template Mods)",
    )
    parser.add_argument(
        "--validate-registry",
        type=Path,
        default=None,
        help="Optional path to registry/mods.json to validate",
    )
    parser.add_argument(
        "--validate-store",
        type=Path,
        default=None,
        help="Optional path to mod-store/catalog.json to validate",
    )
    parser.add_argument(
        "--validate-submissions",
        type=Path,
        default=None,
        help="Optional path to mod-store/submissions/ directory to validate",
    )
    parser.add_argument(
        "--validate-template",
        action="store_true",
        help="Also validate mods/_template/mod.json without packaging it",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run validation checks without writing ZIP archives",
    )
    args = parser.parse_args(argv)

    try:
        if args.validate_registry is not None:
            reg = validate_registry(args.validate_registry, mods_dir=args.mods_dir)
            print(f"[OK] Registry valid: {args.validate_registry} ({len(reg['mods'])} mod entry/entries)")

        if args.validate_store is not None:
            store = validate_store_catalog(args.validate_store, mods_dir=args.mods_dir)
            print(f"[OK] Mod Store catalog valid: {args.validate_store} ({len(store['mods'])} mod entry/entries)")

        if args.validate_submissions is not None:
            sub_count = validate_store_submissions(args.validate_submissions, mods_dir=args.mods_dir)
            print(f"[OK] Mod Store submissions valid: {args.validate_submissions} ({sub_count} submission file(s))")

        if args.validate_template:
            tpl_dir = args.mods_dir / "_template"
            validate_mod_dir(tpl_dir, enforce_folder_match=False)
            print(f"[OK] Starter template valid: {tpl_dir / 'mod.json'}")

        mod_dirs = discover_packable_mods(args.mods_dir, selected=args.mod or None)
        if not mod_dirs:
            if args.validate_only and (
                args.validate_registry is not None
                or args.validate_store is not None
                or args.validate_submissions is not None
                or args.validate_template
            ):
                print(f"[OK] No unpacked Mods under {args.mods_dir}; validation checks passed.")
                return 0
            raise ManifestValidationError(f"No packable Mods found under {args.mods_dir}")

        if args.validate_only:
            for mod_dir in mod_dirs:
                manifest = validate_mod_dir(mod_dir, enforce_folder_match=True)
                print(f"[OK] Manifest valid: {manifest['id']} v{manifest['version']}")
            return 0

        checksum_lines: list[str] = []
        for mod_dir in mod_dirs:
            archive_path, digest = package_single_mod(mod_dir, args.output_dir)
            checksum_lines.append(f"{digest}  {archive_path.name}")
            print(f"[PACKAGED] {archive_path}  sha256={digest}")

        sums_path = args.output_dir / "SHA256SUMS.txt"
        sums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
        print(f"[OK] Wrote {sums_path} ({len(checksum_lines)} archive(s))")
        return 0
    except ManifestValidationError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
