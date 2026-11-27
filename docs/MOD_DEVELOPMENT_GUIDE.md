# Aether Nebula Mod 插件开发手册（Schema v1 · 适用于 v1.3.2）

本手册面向希望为 **Aether Nebula** 开发功能扩展（Mod）的开发者。

Aether Nebula 的 Mod 系统采用 **「目录即插件 + 声明式权限 + 零 HTTP IPC + 加密盘隔离」** 架构：无需修改或重新编译主程序（`Nebula.exe` / `Aether Nebula.app` / `aether-nebula`），将 Mod 目录放入 `mods/` 即可热重载生效。

---

## 1. 架构概览与安全红线

开发任何 Nebula Mod 时，必须遵守以下 5 条设计原则：

1. **零本地 HTTP 管理端口**：Mod 前后端通信全部通过宿主 PyWebView IPC（`invoke_mod`）完成，**严禁**在 Mod 内自起 `flask`、`fastapi`、`aiohttp`、`http.server` 等监听端口。
2. **敏感数据只进工作区（Vault）**：所有持久化数据（SQLite、Token、配置、缓存）必须写入 `context.get_data_dir()`（实际路径为 `{vault_root}/mods/{mod_id}/`），**严禁**写入系统盘临时目录或 Mod 安装目录。
3. **严禁直连泄漏真实 IP**：访问外部网站应通过 `context.create_proxy_http_client(profile_id)` 经该环境的 `socks5://127.0.0.1:{local_port}` 发出，或通过受控指纹浏览器发起；仅在用户明确确认后才可传 `allow_direct=True`。
4. **最小权限声明**：Mod 只能调用在 `mod.json` 的 `permissions` 中显式声明的宿主能力，未声明的调用会被 `ModPermissionError` 拦截。
5. **优雅释放文件锁**：若 Mod 打开了 SQLite 数据库或文件句柄，**必须**实现 `on_vault_close()` 并关闭连接，确保用户点击「安全退出全部」或卸载 VeraCrypt 加密盘时无残留锁。

---

## 2. 目录结构与三端加载路径

### 2.1 Mod 存放位置与优先级
Nebula 启动或执行 **「Mod 扩展 → 热重载 Mods」** 时，按以下优先级扫描：

1. **外部可插拔目录（优先，可覆盖同名内置 Mod）**：`{app_dir}/mods/<mod_id>/mod.json`
   - **源码运行**：`{应用目录或加密盘}/mods/<mod_id>/`
   - **Windows 安装版 / 便携版**：`Nebula.exe` 同级的 `mods/<mod_id>/`（安装器已对该目录赋予普通用户写权限）
   - **macOS `.app`**：`Aether Nebula.app` 同级目录下的 `mods/<mod_id>/`（或当 `.app` 位于只读目录时的 `~/Library/Application Support/Aether Nebula/mods/<mod_id>/`）
   - **Linux 便携版**：`aether-nebula` 同级的 `mods/<mod_id>/`
2. **内置只读回退目录**（仅冻结打包时）：`{resource_dir}/mods/<mod_id>/`

> 外部目录优先级更高：放置与内置 Mod 同名的 `<mod_id>` 目录即可热覆盖，无需重新打包主程序。

### 2.2 标准目录布局
```text
mods/
└── my_mod/                 # 目录名必须与 mod.json 中的 id 完全一致
    ├── mod.json            # 必填：Mod 清单与权限声明
    ├── backend.py          # 必填：Python 后端入口（需导出 create_mod）
    ├── helper.py           # 可选：其他子模块（支持 from .helper import ...）
    ├── panel.html          # 可选：前端弹窗 HTML 片段
    ├── panel.js            # 可选：前端交互脚本
    └── panel.css           # 可选：前端样式表（建议使用 v1.3.2 主题 CSS 变量）
```

### 2.3 模块隔离与容错
- 宿主将每个 Mod 挂载在独立命名空间 `nebula_mods.<mod_id>` 下，可在 `backend.py` 内自由使用相对导入（如 `from .store import MyStore`），不会与其他 Mod 的同名文件冲突；
- 单个 Mod 清单非法、导入失败或回调异常时，仅记录在该 Mod 的 `load_error` 字段中，**不影响主程序与其他 Mod 运行**。

---

## 3. `mod.json` 清单规范

```json
{
  "schema_version": 1,
  "id": "my_mod",
  "name": "我的示例扩展",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "一句话说明 Mod 的核心能力。",
  "platforms": ["windows", "macos", "linux"],
  "backend": "backend.py",
  "ui": {
    "entry": "panel.html",
    "script": "panel.js",
    "style": "panel.css",
    "mount_points": ["topbar", "profile_row"],
    "topbar_label": "示例扩展",
    "profile_row_label": "示例",
    "modal_size": "lg"
  },
  "permissions": [
    "vault_storage",
    "profiles_read"
  ]
}
```

### 字段说明
| 字段 | 必填 | 说明 |
| :--- | :---: | :--- |
| `schema_version` | 是 | 固定填 `1` |
| `id` | 是 | 唯一标识，正则 `^[a-z0-9][a-z0-9_-]{0,31}$`，**必须与目录名完全一致** |
| `name` | 是 | 显示名称 |
| `version` | 否 | 语义化版本号（如 `"1.0.0"`） |
| `author` | 否 | 作者名 |
| `description` | 否 | 简介，展示在「Mod 扩展管理」弹窗 |
| `platforms` | 否 | 支持平台数组：`"windows"` / `"macos"` / `"linux"`，默认全平台 |
| `backend` | 否 | 后端入口相对路径，默认 `"backend.py"`（禁止绝对路径与 `..` 越界） |
| `ui.entry` | 否 | 前端 HTML 模板相对路径；省略则视为纯后台 Mod |
| `ui.script` | 否 | 前端 JS 相对路径 |
| `ui.style` | 否 | 前端 CSS 相对路径 |
| `ui.mount_points` | 否 | 界面入口挂载点数组：`"topbar"`（顶栏按钮）、`"profile_row"`（环境行入口）、`"toolbar"`（主工具栏批量按钮）、`"inline_panel"`（主界面可折叠内联工作台） |
| `ui.topbar_label` | 否 | 顶栏按钮文字 |
| `ui.profile_row_label` | 否 | 环境行弹窗入口文字（建议 2~4 字） |
| `ui.modal_size` | 否 | 弹窗宽度，可选 `"lg"` 或 `"xl"` |
| `ui.inline_panel` | 否 | `true` 时允许在主界面环境列表上方展开内联面板（无需弹窗遮挡主表格） |
| `ui.inline_panel_title` | 否 | 内联工作台标题 |
| `ui.profile_table_columns` | 否 | 外置到主环境列表表格的动态状态列数组：`[{ "id", "label", "width", "default_visible" }]`（用户可在工具栏「列显示」中自由显隐） |
| `ui.profile_row_actions` | 否 | 外置到环境行「快捷操作」区的声明式动作按钮数组：`[{ "id", "label", "action", "style", "title", "confirm", "refresh_columns" }]` |
| `ui.toolbar_actions` | 否 | 外置到主列表工具栏的批量快捷动作数组，点击时自动携带当前可见环境 `profile_ids` |
| `permissions` | 否 | 权限白名单数组，见下表 |

### 可声明权限（`permissions`）
| 权限名 | 允许调用的 `ModContext` 方法 |
| :--- | :--- |
| `vault_storage` | `context.get_data_dir()`（读写 `{vault_root}/mods/{mod_id}/`） |
| `profiles_read` | `list_profiles()`、`get_profile()`、`is_profile_running()`、`ensure_profile_gateway()` |
| `profiles_write` | `update_profile_meta(profile_id, *, name=None, notes=None)`（轻量修改环境名称与备注） |
| `browser_cdp` | `launch_profile()`、`launch_profile_with_cdp()`、`stop_profile()` |
| `proxy_http` | `create_proxy_http_client(profile_id, ...)` |

### 主界面外置列与快捷动作协议（向后兼容 Schema v1）
若你的 Mod 在 `mod.json` 中声明了 `ui.profile_table_columns`，宿主在刷新环境列表时会自动调用 Mod 实例的 `get_profile_columns(profile_ids: list[int])` 方法（若未定义该方法，则回退调用 `handle_action("get_profile_columns", {"profile_ids": [...]})`），返回值格式为：

```python
{
    "1": {
        "ai_account": {
            "text": "GPT · alice@example.com",
            "subtext": "Plus · 剩余 82%",
            "badge": "有效",
            "tone": "emerald",  # emerald | sky | amber | rose | slate | muted
            "title": "悬浮完整提示文案",
        }
    }
}
```

若声明了 `ui.profile_row_actions`，主界面会将按钮直接渲染在对应环境行的快捷操作区域（或「更多 ▾」菜单中）；点击时宿主调用 `invoke_mod(mod_id, item.action, {"profile_id": row.id})`：
- 返回值中若含 `{"open_modal": True}`，宿主会自动打开该 Mod 的面板并自动选中当前环境；
- 若 `item.refresh_columns` 为 `true`（默认），执行完毕后宿主会自动刷新外置列数据与主列表状态。

---

## 4. 后端开发指南（Python）

### 4.1 入口约定与生命周期钩子
`backend.py` 必须导出 `create_mod(context)` 工厂函数，返回包含 `handle_action(action, payload)` 的对象：

```python
from pathlib import Path
from typing import Any


class MyMod:
    def __init__(self, context: Any) -> None:
        self.ctx = context

    # 【必填】处理前端通过 bridge.invoke(action, payload) 发来的所有调用
    def handle_action(self, action: str, payload: dict[str, Any]) -> Any:
        if action == "ping":
            return {"pong": True, "mod_id": self.ctx.mod_id}
        raise ValueError(f"未知操作: {action}")

    # 【可选】工作区挂载成功（或热重载且工作区已挂载）时触发
    # data_dir 仅在声明 vault_storage 权限时非 None
    def on_vault_open(self, data_dir: Path | None) -> None:
        pass

    # 【可选】安全退出 / 切换工作区 / 热重载前触发；务必关闭 DB 连接与文件句柄
    def on_vault_close(self) -> None:
        pass

    # 【可选】用户点击「一键备份」时触发；可将快照写入 backup_dir 并返回已备份文件路径列表
    def on_backup(self, backup_dir: Path) -> list[str]:
        return []


def create_mod(context: Any) -> MyMod:
    return MyMod(context)
```

> **错误处理规范**：在 `handle_action` 中直接抛出 `ValueError` 或 `ModError`，宿主会自动封装为标准 IPC 响应 `{"ok": False, "data": None, "error": "..."}`，前端 `bridge.invoke()` 会自动以该消息 reject。

### 4.2 `ModContext` SDK 完整参考（对齐 `mod_manager.py`）
| 属性 / 方法 | 所需权限 | 说明 |
| :--- | :--- | :--- |
| `ctx.mod_id` | 无 | 当前 Mod 的 ID 字符串 |
| `ctx.mod_dir` | 无 | 当前 Mod 安装目录 `Path`（只读） |
| `ctx.manifest` | 无 | 解析后的 `mod.json` 字典副本 |
| `ctx.permissions` | 无 | 已声明权限的 `frozenset[str]` |
| `ctx.app_version` | 无 | Nebula 主程序版本号（如 `"1.3.2"`） |
| `ctx.host_os` | 无 | 当前宿主机系统：`"windows"` / `"macos"` / `"linux"` |
| `ctx.is_vault_mounted()` | 无 | 当前工作区是否已挂载 |
| `ctx.get_data_dir()` | `vault_storage` | 返回并自动创建 `{vault_root}/mods/{mod_id}/` |
| `ctx.list_profiles()` | `profiles_read` | 返回所有环境列表快照（含名称、备注 `notes`、分组、节点、端口与运行态信息） |
| `ctx.get_profile(profile_id)` | `profiles_read` | 获取单个环境详情字典或 `None` |
| `ctx.is_profile_running(profile_id)` | `profiles_read` | 检查该环境浏览器是否运行中 |
| `ctx.update_profile_meta(profile_id, *, name=None, notes=None)` | `profiles_write` | 轻量更新指定环境的显示名称与/或备注（不重启代理网关） |
| `ctx.ensure_profile_gateway(profile_id, *, allow_direct=False)` | `profiles_read` | 校验环境代理节点/端口并确保 Xray/Mihomo 已启动；无节点时传 `allow_direct=True` 才允许裸通 |
| `ctx.launch_profile(profile_id, *, start_url=None, allow_direct=False)` | `browser_cdp` | 以无调试端口的纯净模式启动该环境（`start_url` 仅允许 `about:blank` 或 `https://`） |
| `ctx.launch_profile_with_cdp(profile_id, *, start_url="about:blank", allow_direct=False)` | `browser_cdp` | 启动带临时 `127.0.0.1` CDP 端口的指纹浏览器，返回含 `cdp_port` 的字典（若已在运行会拒绝） |
| `ctx.stop_profile(profile_id, *, keep_direct_gateway=False)` | `browser_cdp` | 优雅关闭运行中的环境浏览器，等待 Chromium 刷盘保存 SQLite；如需关闭后立即重开可设 `keep_direct_gateway=True` |
| `ctx.create_proxy_http_client(profile_id, *, timeout=15.0, follow_redirects=False, allow_direct=False)` | `proxy_http` | 返回强制走 `socks5://127.0.0.1:{local_port}` 且 `trust_env=False` 的 `httpx.Client`（推荐使用 `with` 上下文自动清理资源） |

### 4.3 运行时依赖边界（重要）
在打包版（Windows `Nebula.exe` / macOS `Aether Nebula.app` / Linux `aether-nebula`）中，外部 Mod 可直接导入：
- **Python 标准库**（`sqlite3`、`json`、`socket`、`hashlib`、`base64`、`http.client`、`pathlib`、`threading`、`re`、`datetime`、`urllib` 等）
- **主程序已内置的三方库**：`httpx`（含 `socksio`）、`yaml`（PyYAML）

**不要依赖未随主程序打包的 pip 包**（如 `playwright`、`selenium`、`requests`、`websockets`），否则冻结环境下会报 `ModuleNotFoundError`。若需通过 CDP 控制浏览器，可直接参考内置 官方 `ai_login` Mod 包（`nebula-mod-ai_login-v1.1.0.zip`）中 `cdp_injector.py` 的零依赖纯标准库 WebSocket 客户端实现。

---

## 5. 前端开发指南（HTML / JS / CSS）

### 5.1 挂载与卸载生命周期
当用户打开你的 Mod 面板时，宿主通过 `get_mod_ui(mod_id)` 读取离线文件并按顺序执行：
1. 将 `panel.css` 注入 `<style data-mod-style="{mod_id}">`；
2. 执行 `panel.js`，脚本通过 `window.NebulaMods.register(modId, mountFn)` 注册挂载工厂；
3. 将 `panel.html` 写入弹窗容器 `container` 并调用 `mountFn(container, bridge)`；
4. 关闭弹窗时，若 `mountFn` 返回了 `{ destroy() { ... } }`，宿主会自动调用 `destroy()` 清理定时器或监听。

> **离线红线**：`panel.html` 与 `panel.css` **严禁**引用任何 `http://` 或 `https://` 外部字体/CDN/图片链接，所有图标请使用内联线性 SVG（`stroke-width="1.5"`）。

### 5.2 `bridge` 前端 SDK 参考（对齐 `ui/index.html`）
| 成员 | 说明 |
| :--- | :--- |
| `bridge.modId` | 当前 Mod ID |
| `bridge.context` | 打开上下文对象。从环境列表行按钮打开时包含 `{ profile_id: number }`；顶栏打开时为 `{}` |
| `await bridge.invoke(action, payload)` | 调用后端 `handle_action(action, payload)`；成功直接返回 `data`，失败抛出带 `message` 的 `Error` |
| `bridge.toast(message, type)` | 触发主界面通知，`type` 可选 `'info'` / `'success'` / `'warning'` / `'error'` |
| `await bridge.refreshProfiles()` | 通知主界面刷新环境列表与系统状态（如 Mod 启动/关闭浏览器后调用） |
| `await bridge.confirmDirectProfile(profileObj, opts)` | 当目标环境未绑定代理节点时，弹出宿主统一的「裸直连安全确认弹窗」，返回用户是否确认（`boolean`） |
| `bridge.openBindProfile(profileId)` | 直接在当前 Mod 弹窗上方呼出「编辑环境」弹窗，方便用户即时为环境绑定代理节点 |
| `bridge.quickEditProfileMeta(profileId)` | 直接在当前 Mod 弹窗上方呼出「快捷修改环境名称与备注」面板，修改后自动同步主列表与所有已挂载 Mod |
| `bridge.close()` | 关闭当前 Mod 弹窗 |

### 5.3 v1.3.2 主题 CSS Design Tokens（自动适配浅/深色与双强调色）
从 **v1.3.2** 起，Aether Nebula 采用 **Claude Warm Alabaster（浅色默认）+ Warm Obsidian（暖黑曜石深色）+ Apple macOS Sequoia** 设计系统，并支持 **Claude 陶土暖橙 / Apple 晴空蓝** 一键切换。

Mod 的 `panel.css` 应**全部使用以下 CSS 变量**（切勿写死 `#0f172a` 等暗蓝硬编码），即可自动跟随主界面切换：

| 用途 | CSS 变量 | Light（默认） | Dark |
| :--- | :--- | :--- | :--- |
| 主画布底色 | `var(--bg-canvas)` | `#F7F6F2` | `#171715` |
| 卡片表面 | `var(--bg-surface)` | `#FFFFFF` | `#232320` |
| 弱底色（分段器槽/代码块） | `var(--bg-subtle)` | `#F2F0EA` | `#1B1B18` |
| 浮层底色 | `var(--bg-elevated)` | `#FFFFFF` | `#2B2B27` |
| 1px 暖石细描边 | `var(--border-hairline)` | `#E5E1D8` | `#33322D` |
| 强调描边 | `var(--border-strong)` | `#D2CCC0` | `#47453E` |
| 主 / 次 / 弱文字 | `var(--text-primary)` / `--text-secondary` / `--text-tertiary` | `#1C1B19` / `#6B675E` / `#9A958A` | `#F2F0EA` / `#9C988E` / `#6F6C64` |
| 主强调色（含 10% 柔底） | `var(--accent)` / `var(--accent-soft)` / `var(--accent-fg)` | `#C96442`（或 `#007AFF`） | `#E07B59`（或 `#0A84FF`） |
| 语义色（成功/警告/危险/信息） | `var(--success)` / `--warning` / `--danger` / `--info`（均配套 `-soft`、`-border`、`-text`） | `#1F8A5B` / `#B97305` / `#C83E3E` / `#2563EB` | `#34C77B` / `#F0A93B` / `#F06464` / `#60A5FA` |
| 字体栈与圆角 | `var(--font-sans)` / `var(--font-mono)` / `var(--radius-card)` | `12px` 卡片圆角 | 同左 |

同时可直接复用主界面原子组件类（建议给根容器加专属前缀如 `.mymod-root` 防止样式泄漏）：
- **按钮**：`.btn`、`.btn-xs`、`.btn-primary`、`.btn-emerald`、`.btn-sky`、`.btn-amber`、`.btn-danger`
- **分段控制器**：`.segmented` + `.seg-btn` / `.seg-btn.active`
- **表单与分组设置**：`.input`、`.select`、`.textarea`、`.seq-group`、`.seq-row`
- **徽章与等宽数字**：`.badge`、`.badge-emerald`、`.badge-sky`、`.badge-amber`、`.badge-rose`、`.badge-slate`、`.mono`（自动开启 `tabular-nums`）

---

## 6. 最小可运行示例（Hello World Mod）

在 `mods/hello_mod/` 下新建以下 4 个文件，点击顶栏 **「Mod 扩展 → 热重载 Mods」** 即可体验：

### `mods/hello_mod/mod.json`
```json
{
  "schema_version": 1,
  "id": "hello_mod",
  "name": "Hello 示例",
  "version": "0.1.0",
  "author": "Dev",
  "description": "最小可运行的 Nebula v1.3.2 Mod 示例。",
  "platforms": ["windows", "macos", "linux"],
  "backend": "backend.py",
  "ui": {
    "entry": "panel.html",
    "script": "panel.js",
    "style": "panel.css",
    "mount_points": ["topbar"],
    "topbar_label": "Hello"
  },
  "permissions": ["profiles_read"]
}
```

### `mods/hello_mod/backend.py`
```python
from typing import Any


class HelloMod:
    def __init__(self, context: Any) -> None:
        self.ctx = context

    def handle_action(self, action: str, payload: dict[str, Any]) -> Any:
        if action == "summary":
            profiles = self.ctx.list_profiles()
            return {
                "greeting": f"Hello, {payload.get('who') or 'Nebula'}!",
                "profile_count": len(profiles),
                "app_version": self.ctx.app_version,
                "host_os": self.ctx.host_os,
            }
        raise ValueError(f"未知动作: {action}")


def create_mod(context: Any) -> HelloMod:
    return HelloMod(context)
```

### `mods/hello_mod/panel.html`
```html
<div class="hello-mod-root">
  <div class="hello-mod-bar">
    <input class="input" data-name placeholder="输入你的名字">
    <button class="btn btn-primary" data-go>调用后端</button>
  </div>
  <pre class="mono hello-mod-out" data-out>点击上方按钮调用 Mod 后端...</pre>
</div>
```

### `mods/hello_mod/panel.css`
```css
.hello-mod-root {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.hello-mod-bar {
  display: flex;
  gap: 8px;
}
.hello-mod-out {
  margin: 0;
  padding: 12px 14px;
  border-radius: var(--radius-card, 12px);
  background: var(--bg-subtle);
  border: 1px solid var(--border-hairline);
  color: var(--text-primary);
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
}
```

### `mods/hello_mod/panel.js`
```javascript
(function () {
  window.NebulaMods.register('hello_mod', function (container, bridge) {
    const out = container.querySelector('[data-out]');
    const input = container.querySelector('[data-name]');
    const btn = container.querySelector('[data-go]');

    btn.addEventListener('click', async () => {
      try {
        const res = await bridge.invoke('summary', { who: input.value.trim() });
        out.textContent = JSON.stringify(res, null, 2);
        bridge.toast(res.greeting, 'success');
      } catch (err) {
        bridge.toast(err.message, 'error');
      }
    });

    return { destroy() {} };
  });
})();
```

---

## 7. 完整参考实现：`ai_login` 内置 Mod

仓库内置的生产级 Mod [`ai_login` 官方 Mod 归档](https://github.com/Aetherophas1c/aether-nebula/releases/latest) 完整示范了所有能力：

- `mod.json`：双挂载点（`topbar` + `profile_row`）与全部 4 项权限声明；
- `parsers.py`：ChatGPT / Grok / Claude / Gemini 凭据解析、3800 字节分片 Cookie 构造与敏感文本脱敏；
- `store.py`：写入工作区的独立 WAL SQLite 账号库及在线快照备份；
- `cdp_injector.py`：纯标准库 loopback WebSocket CDP 客户端；
- `backend.py`：`create_mod` 入口、经代理在线验活、CDP 注入与「纯净模式重开」编排；
- `panel.html` / `panel.js` / `panel.css`：适配 v1.3.2 Warm Alabaster / Warm Obsidian 双主题的前端面板。

---

## 8. 调试、热重载与单元测试

### 8.1 开发热重载
修改 `backend.py`、`panel.html`、`panel.js` 或 `panel.css` 后无需重启主程序：
1. 点击左侧栏 **「Mod 扩展」**；
2. 点击 **「热重载 Mods」**（宿主会依次执行 `on_vault_close()` → 清理 `nebula_mods.<id>` 缓存与旧 `<style>` → 重新加载代码 → 执行 `on_vault_open()`）。

### 8.2 端到端单元测试
可参考 客户端内热重载或本地单元测试，使用 `ManagerAPI` + `tmp_path` 编写自动化测试：

```python
import json
import shutil
from PrivateBrowserManager.api import ManagerAPI


def test_my_mod(tmp_path):
    base_dir = tmp_path / "app"
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    shutil.copytree("mods/my_mod", base_dir / "mods" / "my_mod")
    cfg = base_dir / "config.local.json"
    cfg.write_text(json.dumps({"vault_root": str(vault_root)}), encoding="utf-8")

    api = ManagerAPI(config_path=cfg, base_dir=base_dir, auto_start_xray=False)
    try:
        resp = api.invoke_mod("my_mod", "ping", {})
        assert resp["ok"] is True
    finally:
        api.safe_shutdown_all()
```

运行全量测试：
```bash
pytest PrivateBrowserManager/tests -v
```

---

## 9. 分发与安装指南（给最终用户）

1. 将 `mods/<mod_id>/` 打包为 ZIP（**不要**包含 `__pycache__/`、`.pyc` 或任何个人数据库/日志）；
2. 用户解压到 Nebula 安装目录的 `mods/` 下（保证存在 `mods/<mod_id>/mod.json`）；
3. 启动 Nebula 或点击 **「Mod 扩展 → 热重载 Mods」** 即可生效；
4. 卸载时先安全关闭 Nebula，删除 `mods/<mod_id>/` 即可；工作区内的 Mod 数据位于 `{vault_root}/mods/<mod_id>/`，可按需保留或清理。
