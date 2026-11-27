# Third-Party Licenses & Attributions

Aether Nebula incorporates, builds upon, or interoperates with the following open-source projects and font families. Each component retains its own copyright and license terms.

---

## 1. Browser Engine & Patches

| Project | License | Role in Aether Nebula | Upstream |
| :--- | :--- | :--- | :--- |
| **Chromium** | BSD-3-Clause | Base browser engine for hardened Fingerprint-Chromium builds | https://www.chromium.org/ |
| **ungoogled-chromium** | BSD-3-Clause | Privacy-hardened Chromium patch baseline (`158.0.8127.36`) | https://github.com/ungoogled-software/ungoogled-chromium |

---

## 2. Proxy & Network Core Engines

Aether Nebula invokes proxy core binaries as **standalone, unmodified external processes** over local IPC/configuration files; their source code is not statically linked into the Python management console.

| Project | License | Role in Aether Nebula | Upstream |
| :--- | :--- | :--- | :--- |
| **Xray-core** | MPL-2.0 | Primary per-profile SOCKS5 & VLESS/Reality/Relay proxy engine (standalone binary) | https://github.com/XTLS/Xray-core |
| **Mihomo (Clash.Meta)** | GPL-3.0 | Optional secondary subscription & multi-protocol proxy engine (standalone binary) | https://github.com/MetaCubeX/mihomo |

> **Compliance note for binary releases**: When distributing prebuilt release bundles that include unmodified `xray` or `mihomo` binaries, retain their respective upstream license notices (MPL-2.0 / GPL-3.0) and upstream source links in the release notes or package `licenses/` directory.

---

## 3. Desktop Console & Frontend Libraries

| Project | License | Role in Aether Nebula | Upstream |
| :--- | :--- | :--- | :--- |
| **PyWebView** | BSD-3-Clause | Native OS WebView host (`Edge WebView2` / `WKWebView` / `WebKitGTK`) with `http_server=False` IPC | https://github.com/r0x0r/pywebview |
| **Alpine.js** | MIT | Bundled offline reactive UI framework (`PrivateBrowserManager/assets/alpine.min.js`) | https://github.com/alpinejs/alpine |
| **httpx** | BSD-3-Clause | Proxy-routed HTTP client for GeoIP probing and Mod network helpers | https://github.com/encode/httpx |
| **socksio** | BSD-3-Clause | Sans-I/O SOCKS5 protocol support used by `httpx[socks]` | https://github.com/sethmlarson/socksio |
| **PyYAML** | MIT | YAML parser/emitter for Clash/Mihomo subscriptions and configs | https://github.com/yaml/pyyaml |

---

## 4. Bundled Open-Source Metric-Compatible Font Packs

Release distributions ship open-source metric-compatible font families under `bin/fonts/` to eliminate cross-OS font fallback leakage, CJK/Emoji tofu boxes (`□`), and symbol-font garbling without redistributing proprietary OS fonts.

| Font Family | License | Emulated Role / Metric Compatibility |
| :--- | :--- | :--- |
| **Selawik** | MIT | Open-source metric-compatible fallback for Segoe UI |
| **Carlito** | SIL Open Font License 1.1 (OFL-1.1) | Open-source metric-compatible fallback for Calibri |
| **Caladea** | Apache License 2.0 | Open-source metric-compatible fallback for Cambria |
| **Gelasio** | SIL Open Font License 1.1 (OFL-1.1) | Open-source metric-compatible fallback for Georgia |
| **Liberation Fonts** (Sans / Serif / Mono) | SIL Open Font License 1.1 (OFL-1.1) | Open-source metric-compatible fallbacks for Arial, Times New Roman, and Courier New |
| **DejaVu Fonts** | Bitstream Vera / Arev License | Broad Unicode / Linux desktop font coverage |
| **Ubuntu Font Family** | Ubuntu Font Licence 1.0 (UFL-1.0) | Linux desktop UI typography |
| **PT Sans / PT Serif** | SIL Open Font License 1.1 (OFL-1.1) | Extended Latin/Cyrillic proportional sans & serif coverage |
| **Noto Sans CJK & Noto Color Emoji** | SIL Open Font License 1.1 (OFL-1.1) | Anti-tofu CJK ideograph and color emoji fallback |
| **OpenSymbol** | GNU Lesser General Public License (LGPL-3.0) | Mathematical & symbol glyph coverage |

> **Proprietary OS fonts are NEVER distributed**: The optional helper `scripts/sync_os_fonts.py` is strictly for local, private use on machines where the user already holds a valid Windows or macOS license. Do not commit proprietary font files to this repository or upload them to public releases.
