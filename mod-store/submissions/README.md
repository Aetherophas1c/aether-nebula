# Mod 商城社区投稿目录 (`mod-store/submissions/`)

本目录采用 **“1 个 Mod = 1 个独立 JSON 文件”** 的结构，便于社区开发者并发提 PR 上架到未来的 Aether Nebula Mod 商城，而不会互相修改 `catalog.json` 导致合并冲突。

## 投稿步骤

1. 基于 [`mods/_template/`](../../mods/_template/) 开发你的 Mod，并遵守 [`docs/MOD_DEVELOPMENT_GUIDE.md`](../../docs/MOD_DEVELOPMENT_GUIDE.md) 安全红线（零外部 UI URL、仅写加密盘 `context.get_data_dir()`、最小权限声明）。
2. 使用官方打包工具生成可复现 ZIP 与 SHA-256：
   ```bash
   python3 scripts/package_mods.py --mod <your_mod_id> --output-dir mod-store/packages
   ```
3. 将生成的 `nebula-mod-<your_mod_id>-v<version>.zip` 发布到你自己的公开 GitHub Release（或经审核的镜像源）。
4. 在本目录下新增 `<your_mod_id>.json`（字段规范见 [`../schema/submission.schema.json`](../schema/submission.schema.json)）：
   ```json
   {
     "id": "my_quota_monitor",
     "name": "额度与重置卡监控",
     "tagline": "在主界面环境表外置 5 小时额度与每周额度状态列",
     "version": "1.0.0",
     "author": "your-github-handle",
     "license": "MIT",
     "description": "通过当前环境绑定的代理节点拉取额度状态，在环境表自定义列中实时展示并支持一键重置。",
     "category": "quota-billing",
     "tags": ["quota", "columns", "automation"],
     "official": false,
     "verified": false,
     "bundled": false,
     "platforms": ["windows", "macos", "linux"],
     "permissions": ["vault_storage", "profiles_read", "proxy_http"],
     "ui_slots": ["profile_table_columns", "profile_row_actions", "toolbar_actions", "inline_panel"],
     "min_nebula_version": "1.3.0",
     "download_url": "https://github.com/<owner>/<repo>/releases/download/v1.0.0/nebula-mod-my_quota_monitor-v1.0.0.zip",
     "sha256": "<64-char-lowercase-sha256>",
     "homepage": "https://github.com/<owner>/<repo>",
     "source_url": "https://github.com/<owner>/<repo>"
   }
   ```
5. 运行校验并提 PR：
   ```bash
   python3 scripts/package_mods.py --validate-store mod-store/catalog.json --validate-submissions mod-store/submissions --validate-only
   ```
