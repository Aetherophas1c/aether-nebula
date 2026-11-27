## Summary
Briefly describe the motivation, scope, and key changes in this PR.

Closes #

## Type of Change
- [ ] Bug fix
- [ ] New feature / enhancement
- [ ] Chromium patch stack (`chromium-patches/v158/`)
- [ ] Mod / Mod SDK / Registry (`PrivateBrowserManager/mods/` or `registry/mods.json`)
- [ ] Documentation / Governance / CI

## Verification Performed
List the commands you ran locally and their results:
- [ ] `pytest PrivateBrowserManager/tests -v`
- [ ] `python3 scripts/package_mods.py --validate-registry registry/mods.json --validate-template --output-dir /tmp/mods_dist`
- [ ] Manual smoke test on target OS (specify OS/arch): ``

## Architecture & Security Red-Line Checklist
- [ ] **Zero UI HTTP ports**: `webview.start(..., http_server=False)` preserved; no forbidden HTTP server imports in UI/manager/Mods.
- [ ] **Zero external UI URLs**: No `http://` or `https://` links added to `ui/index.html`, `assets/styles.css`, or Mod `panel.html` / `panel.css`.
- [ ] **Vault isolation**: No sensitive files written outside `vault_root`; `on_vault_close()` cleans up handles.
- [ ] **Zero secrets / binaries**: No `vault.db`, `config.local.json`, real proxy credentials, proprietary fonts, or compiled binaries committed.
- [ ] **Patch hygiene** (if modifying `chromium-patches/`): LF-only line endings and `patch -p1 --fuzz=0` verified.
