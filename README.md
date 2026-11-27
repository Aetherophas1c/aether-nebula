# Aether Nebula — 官方客户端下载与 Mod 商城仓库

**Aether Nebula** 是一款跨平台隐私防关联指纹浏览器管理控制台（桌面原生 WebView 零管理端口架构 + **Xray / Mihomo** 双引擎代理隔离 + 深度定制 **Fingerprint-Chromium `158.0.8127.36`** 内核 + 可插拔 Mod 扩展体系）。

> 本仓库为 **Aether Nebula 官方客户端发布分发、使用文档与 Mod 商城（`mod-store/`）公开仓库**。所有平台客户端安装包与官方 Mod 归档均托管在 **[GitHub Releases](https://github.com/Aetherophas1c/aether-nebula/releases)**。

---

## 最新版本下载：`v1.3.2`

前往 **[v1.3.2 Release 页面](https://github.com/Aetherophas1c/aether-nebula/releases/tag/v1.3.2)** 或直接点击下方链接下载（内置硬核定制 `Fingerprint-Chromium 158.0.8127.36`、三端离线字体包及 `Xray` / `Mihomo` 双代理核心，开箱即用）：

| 操作系统与架构 | 安装包 / 便携版下载直链 | 大小 |
| :--- | :--- | ---: |
| **Windows x64（安装版，推荐）** | [Aether-Nebula-Setup-1.3.2-x64.exe](https://github.com/Aetherophas1c/aether-nebula/releases/download/v1.3.2/Aether-Nebula-Setup-1.3.2-x64.exe) | 226 MB |
| **Windows x64（免安装便携版）** | [Aether-Nebula-v1.3.2-win-x64-portable.zip](https://github.com/Aetherophas1c/aether-nebula/releases/download/v1.3.2/Aether-Nebula-v1.3.2-win-x64-portable.zip) | 298 MB |
| **Windows ARM64（安装版）** | [Aether-Nebula-Setup-1.3.2-arm64.exe](https://github.com/Aetherophas1c/aether-nebula/releases/download/v1.3.2/Aether-Nebula-Setup-1.3.2-arm64.exe) | 210 MB |
| **Windows ARM64（便携版）** | [Aether-Nebula-v1.3.2-win-arm64-portable.zip](https://github.com/Aetherophas1c/aether-nebula/releases/download/v1.3.2/Aether-Nebula-v1.3.2-win-arm64-portable.zip) | 283 MB |
| **macOS Apple Silicon (M1/M2/M3/M4)** | [Aether-Nebula-v1.3.2-macos-arm64.dmg](https://github.com/Aetherophas1c/aether-nebula/releases/download/v1.3.2/Aether-Nebula-v1.3.2-macos-arm64.dmg) | 274 MB |
| **macOS Intel (`x86_64`)** | [Aether-Nebula-v1.3.2-macos-x86_64.dmg](https://github.com/Aetherophas1c/aether-nebula/releases/download/v1.3.2/Aether-Nebula-v1.3.2-macos-x86_64.dmg) | 293 MB |
| **Linux x64（便携版）** | [Aether-Nebula-v1.3.2-linux-x64.tar.gz](https://github.com/Aetherophas1c/aether-nebula/releases/download/v1.3.2/Aether-Nebula-v1.3.2-linux-x64.tar.gz) | 386 MB |
| **Linux ARM64（便携版）** | [Aether-Nebula-v1.3.2-linux-arm64.tar.gz](https://github.com/Aetherophas1c/aether-nebula/releases/download/v1.3.2/Aether-Nebula-v1.3.2-linux-arm64.tar.gz) | 440 MB |
| **官方 Mod 归档 (`ai_login` v1.1.0)** | [nebula-mod-ai_login-v1.1.0.zip](https://github.com/Aetherophas1c/aether-nebula/releases/download/v1.3.2/nebula-mod-ai_login-v1.1.0.zip) | 31 KB |
| **SHA-256 校验清单** | [SHA256SUMS.txt](https://github.com/Aetherophas1c/aether-nebula/releases/download/v1.3.2/SHA256SUMS.txt) | 934 B |

### 首次安装说明

- **Windows**：直接运行 `Aether-Nebula-Setup-1.3.2-<arch>.exe`（自动检查 WebView2 运行时与防火墙防直连规则），或解压 `portable.zip` 运行 `Nebula.exe`。
- **macOS**：将 `Aether Nebula.app` 拖入「应用程序（Applications）」。因应用采用本地 Ad-hoc 签名，首次打开若系统提示无法验证开发者，在「终端 (Terminal)」执行一次以下命令（无需密码，1 秒完成）：
  ```bash
  xattr -cr "/Applications/Aether Nebula.app"
  ```
- **Linux**：解压 `.tar.gz` 后运行 `./aether-nebula`（可按需配置 `aether-nebula.desktop.in` 快捷方式）。
- **校验完整性**：下载 `SHA256SUMS.txt` 后执行 `sha256sum -c SHA256SUMS.txt --ignore-missing`（Windows PowerShell 使用 `Get-FileHash <文件名> -Algorithm SHA256`）。

---

## v1.3.2 更新亮点

- **Windows / macOS / Linux 三端文件选择框彻底修复（默认 `.nebula` 扩展名）**：消除 PyWebView `parse_file_type` 拒绝含连字符扩展名导致的点击无反应问题；macOS 改用 `file_types=()` 防止自定义后缀灰显；显式传入初始目录并透传真实错误，同时新增导入弹窗文件拖拽兜底（完全向后兼容 `.nebula-profile` / `.zip`）。
- **macOS 加密重载横幅与登录态丢失彻底修复（同步覆盖 Linux）**：在正常 GUI 启动与离线 CDP Cookie 迁移中统一启用 macOS `--use-mock-keychain`（已核验 Chromium 158 `FakeKeychainV2` 确定性持久化密钥）与 Linux `--password-store=basic`，并在导入前自动清理跨平台 `Local State.os_crypt` 与旧 Cookie 库。
- **CDP Cookie 迁移与冷启动恢复加固**：完整修正 `__Host-*`、`__Secure-*`、Host-Only 与 `.domain` 作用域规范化、三级降级注入、写入后实存核验、慢速主机 `NetworkService` 冷启动重启自动恢复与 15s WAL 刷盘等待；Cookie 未完全还原时前端改弹琥珀色告警卡片。
- **三端剪贴板与配置胶囊防截断增强**：Windows 增至 `25×20ms` 重试 + `GlobalSize` 有界读取；macOS 强制 UTF-8 环境与 8s 超时；Linux 按 Wayland/X11 自动排序并用 `DEVNULL` 管道防卡死；自动清理 BOM/零宽字符/Markdown 代码块并识别微信/QQ截断胶囊，新增过期/核心 Cookie 过滤开关。

### v1.3.1 更新内容

- **Windows 中文 / 非 ASCII 用户名启动闪退修复**：安装程序写出纯 ASCII `\uXXXX` + 无 BOM UTF-8 配置；客户端读取端自动兼容并无感自愈旧版 GBK / BOM 编码的 `config.local.json`。
- **快捷操作列紧凑排版优化**：行内默认恢复 `打开 / 关闭` + `测速` + `编辑` + `更多 ▾` 单排紧凑布局，所有 Mod 行动作默认收纳至 `更多 ▾` 并动态去重；工具栏「列显示」下拉面板新增持久化「行内快捷按钮」外置开关。

### v1.3.0 基础核心特性

- **Claude Warm Alabaster + Apple macOS Sequoia 双主题桌面 UI**：浅色暖羊皮纸与深色暖黑曜石双主题、双强调色切换；彻底移除 `backdrop-filter` 根治 Windows WebView2 合成层丢帧空白与表头叠字。
- **自定义环境列表列 + 固定左侧标识列 + 紧凑操作列**：支持自由勾选显隐各列并持久化、1 次点击行内快捷编辑名称/备注（不重启代理）、紧凑快捷操作与不溢出 `更多 ▾` 浮层。
- **Mod 能力全面外置**：插件可将自定义状态列、环境行快捷按钮、工具栏批量按钮与可折叠内联工作台直接投射到主界面（内置 `ai_login` 已升级至 `v1.1.0`）。
- **代理节点分组与分组选择器**：支持节点分组增删改查、筛选、批量分配，环境/链式代理/导入弹窗按分组 `<optgroup>` 选择。
- **跨系统单环境导出/导入 & 剪贴板迁移**：支持 `.nebula-profile` 加密包与紧凑剪贴板胶囊，自动剥离 `os_crypt` 并支持跨系统 CDP Cookie 迁移。
- **离线 Chromium `158.0.8127.36` 真实浏览足迹生成**：自动生成符合 Chromium 158 Schema 的历史记录、高频站点、书签与偏好设置。

---

## Mod 商城与开发者文档

| 资源 | 路径 | 说明 |
| :--- | :--- | :--- |
| **Mod 商城预留区** | [`mod-store/`](mod-store/README.md) | 商城主索引 `catalog.json`、分类定义 `categories.json`、JSON Schema、社区投稿 `submissions/`、图标资源 `assets/` |
| **轻量 Mod 索引** | [`registry/mods.json`](registry/mods.json) | 精简版机器可读 Mod 清单与 SHA-256 校验和 |
| **Mod 开发模板** | [`mods/_template/`](mods/_template/README.md) | 官方空白 Mod 脚手架（演示外置列、快捷按钮、工具栏与加密盘隔离存储） |
| **Mod 打包校验工具** | [`scripts/package_mods.py`](scripts/package_mods.py) | 一键校验清单、检查离线规范并打包可复现 ZIP + `SHA256SUMS.txt` |
| **Mod 开发手册** | [`docs/MOD_DEVELOPMENT_GUIDE.md`](docs/MOD_DEVELOPMENT_GUIDE.md) | Schema v1 规范、权限白名单、`ModContext` 与前端 `bridge` 接口文档 |
| **Local HTTP API 手册** | [`docs/LOCAL_API_GUIDE.md`](docs/LOCAL_API_GUIDE.md) | 可选本地自动化 REST API 及 curl / Playwright / Puppeteer / Selenium 接入示例 |
| **安全与合规说明** | [`SECURITY.md`](SECURITY.md) · [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) | 安全漏洞披露渠道与第三方运行时组件许可证声明 |

---

## 反馈与社区

- **提交 Bug / 功能建议 / Mod 上架申请**：请使用 [GitHub Issues](https://github.com/Aetherophas1c/aether-nebula/issues) 模板或向 `mod-store/submissions/` 提交 PR。
- **使用交流**：欢迎在 [GitHub Discussions](https://github.com/Aetherophas1c/aether-nebula/discussions) 讨论。
