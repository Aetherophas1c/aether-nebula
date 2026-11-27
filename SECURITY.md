# Security Policy

Security and privacy isolation are foundational to **Aether Nebula**. We appreciate responsible disclosure from security researchers and community contributors.

---

## Supported Versions

| Version | Security Support Status |
| :--- | :--- |
| `1.3.x` | Supported (active development & security patches) |
| `1.2.x` | Supported (security fixes & maintenance) |
| `< 1.2.0` | Unsupported — please upgrade to `1.2.x` or newer |

---

## Reporting a Vulnerability

**Please do NOT open a public GitHub Issue for security vulnerabilities.**

Instead, report vulnerabilities privately through one of the following channels:

1. **GitHub Private Vulnerability Reporting (Preferred)**:
   - Open the repository's **Security** tab → **Advisories** → **Report a vulnerability**.
2. **Direct Maintainer Contact**:
   - If GitHub Security Advisories are unavailable, contact the organization maintainers privately via the security contact listed on the GitHub Organization profile (`Aetherophas1c`).

### What to Include
- Affected Aether Nebula version, OS / architecture, and Chromium kernel version (if applicable).
- Clear reproduction steps or a minimal proof-of-concept.
- Security impact assessment (e.g., IP/DNS leak, Vault escape, Mod permission bypass, Local API auth bypass, CDP exposure).
- **Important**: Sanitize all logs before sharing. Never send real proxy credentials, VeraCrypt passphrases, `vault.db`, or live session cookies.

### Response Timeline
- **Initial acknowledgment**: within **72 hours**.
- **Triage & severity assessment**: within **7 days**.
- **Coordinated disclosure**: we will work with you to validate a fix and publish an advisory before public details are released.

---

## Security Architecture Summary

Aether Nebula enforces defense-in-depth across four layers:

1. **Encrypted Vault Gatekeeper**
   - All sensitive artifacts (`vault.db`, browser profiles, cookies, generated `xray_config.json` / `mihomo_config.yaml`, and Mod databases under `{vault_root}/mods/{mod_id}/`) reside strictly inside the mounted Vault directory (such as a VeraCrypt encrypted volume).
   - If the Vault is not mounted, the Gatekeeper blocks all read/write operations without ever auto-creating a directory on the host OS disk.
   - `safe_shutdown_all()` terminates managed browsers and proxy cores and closes all DB/Mod file handles cleanly prior to unmounting.
2. **Zero-HTTP-Port UI & Offline Frontend**
   - The PyWebView console launches with `http_server=False` and `private_mode=True`, communicating purely via native JS-to-Python IPC.
   - Frontend HTML/CSS assets are statically audited by CI to guarantee zero external `http://` / `https://` requests.
3. **Loopback-Only Opt-In Local Automation API**
   - Disabled by default; when explicitly enabled, binds strictly to `127.0.0.1` on a configured port.
   - Protected by constant-time token comparison (`Authorization: Bearer <key>` or `X-API-Key`) and denies wildcard cross-origin access.
4. **Proxy & Mod Isolation**
   - Each profile receives a dedicated local SOCKS5 port (`127.0.0.1:<port>`), blackhole-first proxy fallback, and Chromium `--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1` to prevent DNS leaks.
   - Ephemeral CDP ports used by automation or Mods bind exclusively to `127.0.0.1` with `--remote-allow-origins=http://127.0.0.1:<port>` and optional clean-mode browser reopen.
   - Mods run under isolated `nebula_mods.<id>` namespaces, enforce path-traversal checks, and can only invoke host capabilities explicitly declared in `mod.json` `permissions`.
5. **Repository Secret Hygiene**
   - CI continuously verifies that no Vault databases, private configs, credentials, or compiled binaries are committed to source control.
