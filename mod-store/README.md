# Aether Nebula Mod Store（Mod 商城预留区）

本目录专为后续建设 **Aether Nebula Mod 商城**（支持静态 Web 商店与桌面端内嵌一键安装）预留标准目录结构、索引 Schema、社区投稿通道与构建约定。

## 目录结构

```text
mod-store/
├── README.md                    # 本说明文档与商城接入协议
├── catalog.json                 # 商城主索引（前端商城 / 客户端 Mod 市场直接消费）
├── categories.json              # 商城分类元数据（中英文名称、图标标识、排序）
├── schema/
│   ├── catalog.schema.json      # catalog.json 的 JSON Schema (Draft 2020-12)
│   └── submission.schema.json   # 社区投稿 submissions/<mod_id>.json 的校验 Schema
├── submissions/
│   ├── README.md                # 社区开发者提交 Mod 上架 PR 指南（1 Mod = 1 文件，避免合并冲突）
│   └── .gitkeep                 # 后续社区投稿文件：<mod_id>.json
├── assets/
│   └── .gitkeep                 # 商城卡片图标 / 预览截图（建议 WebP/PNG，单图 <= 512 KB）
└── packages/
    ├── README.md                # 本地打包暂存说明（正式 ZIP 归档托管于 GitHub Releases，不入 Git）
    └── .gitkeep
```

## 与现有体系的协同关系

- **内置与模板源码**：位于 [`mods/`](../mods/)（内置 `ai_login`、开发脚手架 `_template`）。
- **轻量兼容索引**：[`registry/mods.json`](../registry/mods.json) 保留精简核心字段，供脚本与最小化客户端读取；`mod-store/catalog.json` 在其基础上扩展商城展示字段（分类、标语、标签、UI 槽位能力、包体大小、截图与更新日志）。
- **确定性打包与校验**：统一使用 [`scripts/package_mods.py`](../scripts/package_mods.py) 打包生成 `nebula-mod-<id>-v<version>.zip` 与 `SHA256SUMS.txt`（固定 ZIP 时间戳，字节级可复现）。

## 未来商城前端 / 客户端对接方案

1. **只读索引拉取（零后端起步）**
   - 直接通过 GitHub Raw / Cloudflare Pages / jsDelivr 托管 `mod-store/catalog.json` 与 `mod-store/assets/*`，无需自建数据库即可上线静态 Web Mod 商城。
2. **客户端内嵌一键安装（安全闭环）**
   - 客户端拉取 `catalog.json` 展示卡片与权限清单（`permissions` + `ui_slots`）。
   - 用户确认权限后，客户端下载 `download_url`（强制 HTTPS）到本地临时目录，**严格校验 `sha256`** 匹配后解压到 `{app_dir}/mods/<id>/` 或 `{vault_root}/mods/<id>/` 并热加载。
   - **安全红线**：任何 Mod UI（`panel.html` / `panel.css`）严禁包含 `http://` 或 `https://` 外链；所有敏感凭证只能落盘在加密盘 `context.get_data_dir()`。
3. **社区上架流（PR 驱动，零并发冲突）**
   - 第三方开发者无需直接修改庞大的 `catalog.json`，只需按 [`submissions/README.md`](submissions/README.md) 在 `mod-store/submissions/<mod_id>.json` 新增独立元数据文件并提交 PR；CI 自动校验 Schema、权限白名单、HTTPS 链接与 `sha256`，合并后由维护者或发布工作流汇总进 `catalog.json` 与 `registry/mods.json`。

## 本地校验命令

```bash
python3 scripts/package_mods.py \
  --validate-registry registry/mods.json \
  --validate-store mod-store/catalog.json \
  --validate-template \
  --output-dir mod-store/packages
```
