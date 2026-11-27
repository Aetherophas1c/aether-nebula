# Aether Nebula Official Mod Starter Template (`_template`)

本目录是 **Aether Nebula（Schema v1 / v1.3.0+）** 官方 Mod 开发脚手架。

> **为什么目录名为 `_template`？**
> `ModManager` 会自动忽略以 `.` 或 `_` 开头的目录，因此 `_template/` **永远不会被当作异常插件加载**，也不会被 `scripts/package_mods.py` 打包进发布产物。开发者可直接复制本目录并重命名，5 分钟跑通自定义扩展。

---

## 快速开始（3 步跑通）

1. **复制模板目录**（目录名必须满足 `^[a-z0-9][a-z0-9_-]{0,31}$`）：
   ```bash
   cp -r mods/_template mods/my_mod
   ```
   如需改成其他 ID（例如 `cookie_sync`），请同步修改：
   - 目录名：`mods/cookie_sync/`
   - `mod.json` 中的 `"id": "cookie_sync"`
   - `panel.js` 顶部的 `const MOD_ID = 'cookie_sync';`

2. **热重载生效**：
   启动 Aether Nebula，点击左侧栏 **「Mod 扩展」→「热重载 Mods」** 即可看到新扩展挂载到顶栏、工具栏、环境行操作按钮、主列表自定义列与内联工作台。

3. **打包与校验**：
   ```bash
   python3 scripts/package_mods.py --mod my_mod --output-dir dist/mods
   ```
   生成 `dist/mods/nebula-mod-my_mod-v0.1.0.zip` 与 `SHA256SUMS.txt`，自动校验清单与离线合规性并排除 `__pycache__/`、`*.pyc`、`*.db`、`*.log`。

---

## `mod.json` 扩展槽位说明（v1.3.0+）

本模板完整展示了 Schema v1 基础字段以及新增的可选主界面外置槽位字段：

| 字段 | 说明 |
| :--- | :--- |
| `ui.mount_points` | 挂载入口列表，可选 `"topbar"`、`"profile_row"`、`"toolbar"`、`"inline_panel"` |
| `ui.inline_panel` / `ui.inline_panel_title` | 是否在主界面内联渲染 Mod 工作台及标题 |
| `ui.profile_table_columns` | 注入到主界面环境列表的自定义列（`id`、`label`、`width`、`default_visible`），由后端 `get_profile_columns(profile_ids)` 提供单元格数据 |
| `ui.profile_row_actions` | 注入到每个环境行操作区的快捷按钮（`id`、`label`、`action`、`style`、`title`、`confirm`、`refresh_columns`） |
| `ui.toolbar_actions` | 注入到主界面工具栏的批量快捷按钮（`style` 可选 `default` / `primary` / `emerald` / `sky` / `amber` / `danger`） |
| `permissions` | 最小权限白名单：`vault_storage`、`profiles_read`、`profiles_write`、`browser_cdp`、`proxy_http` |

### `get_profile_columns(profile_ids)` 返回格式

后端方法 `get_profile_columns(self, profile_ids: list[int])`（同时通过 `handle_action("get_profile_columns", {"profile_ids": [...]})` 暴露）返回以 `str(profile_id)` 为键的字典：

```python
{
    "12": {
        "mod_tag": {
            "text": "高权重",
            "subtext": "更新于 2026-11-27",
            "badge": "×3",
            "tone": "emerald",  # emerald | sky | amber | rose | slate | muted
            "title": "悬浮提示多行文案"
        }
    }
}
```

---

## 必须遵守的安全与设计红线

- **零外部 URL**：`panel.html` 与 `panel.css` 严禁出现 `http://` 或 `https://` 链接，图标一律使用内联 `1.5px` 线性 SVG。
- **双主题 Token 适配**：`panel.css` 仅使用主界面 CSS 变量（`--bg-surface`、`--bg-subtle`、`--border-hairline`、`--text-primary`、`--accent` 等），严禁硬编码暗蓝色底色，自动兼容 Claude Warm Alabaster（浅色）与 Warm Obsidian（深色）。
- **Vault 独占存储**：所有 SQLite/配置文件只能写入 `context.get_data_dir()`，并必须在 `on_vault_close()` 中关闭句柄。
- **依赖边界**：仅依赖 Python 标准库及主程序内置的 `httpx` / `PyYAML`，确保冻结打包版直接可用。

完整 SDK 文档请参阅 [`docs/MOD_DEVELOPMENT_GUIDE.md`](../../docs/MOD_DEVELOPMENT_GUIDE.md)。
