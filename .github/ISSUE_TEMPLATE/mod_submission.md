---
name: Mod Submission
about: Submit a community Mod to the Aether Nebula registry catalog (registry/mods.json)
title: "[Mod]: "
labels: ["mod-submission"]
assignees: []
---

## Mod Metadata
- **Mod ID** (`^[a-z0-9][a-z0-9_-]{0,31}$`): ``
- **Display Name**: ``
- **Version**: `` (e.g. `1.0.0`)
- **Author / Maintainer**: ``
- **Minimum Nebula Version**: `` (e.g. `1.3.0`)
- **Supported Platforms**: `windows`, `macos`, `linux`
- **Homepage / Source Repository**: ``
- **Release ZIP Download URL**: ``
- **SHA-256 Checksum** (from `scripts/package_mods.py`): ``

## Short Description
A clear 1–2 sentence description of what this Mod does.

## Declared Permissions (`mod.json`)
Check all permissions declared in `mod.json`:
- [ ] `vault_storage` — Explain what is stored under `{vault_root}/mods/<id>/`:
- [ ] `profiles_read` — Explain why profile metadata is read:
- [ ] `profiles_write` — Explain why profile display name/notes are modified:
- [ ] `browser_cdp` — Explain how CDP / browser launch is used:
- [ ] `proxy_http` — Explain which external domains are contacted via profile proxy:

## Security & Quality Checklist
- [ ] Built and packaged cleanly using `python3 scripts/package_mods.py --mod <id>` (zero `__pycache__/`, `*.pyc`, `*.db`, `*.log`).
- [ ] Zero local HTTP servers started inside the Mod backend.
- [ ] Zero external `http://` / `https://` URLs in `panel.html` or `panel.css`.
- [ ] All persistent data is written exclusively inside `context.get_data_dir()` and all file/DB handles are closed in `on_vault_close()`.
- [ ] UI uses v1.3.0+ CSS Design Tokens (`--bg-surface`, `--text-primary`, `--border-hairline`, `--accent`, etc.) and adapts cleanly to both Light (Warm Alabaster) and Dark (Warm Obsidian) themes.
- [ ] Only uses Python standard library + bundled `httpx` / `PyYAML` (works in frozen releases).
- [ ] Open-source license is clearly stated in the Mod repository.
