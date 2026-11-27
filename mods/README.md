# Aether Nebula Mod 扩展区

本目录提供官方 **Mod 插件开发脚手架（[`_template/`](_template/)）**，配合根目录下的 **[`mod-store/`](../mod-store/README.md)（Mod 商城索引与社区投稿区）** 使用。

## 用户如何安装 Mod

1. 从 [Releases](https://github.com/Aetherophas1c/aether-nebula/releases) 或 [`mod-store/catalog.json`](../mod-store/catalog.json) 获取目标 Mod 的 `.zip` 压缩包并校验 SHA-256。
2. 解压到 Aether Nebula 客户端目录的 `mods/`（或加密盘工作区的 `mods/`）下，确保目录结构为 `mods/<mod_id>/mod.json`。
3. 打开 Aether Nebula → 左侧栏 **「Mod 扩展」→「热重载 Mods」** 即可生效，无需重新编译客户端。

## 开发者如何制作并上架 Mod

1. 复制 [`_template/`](_template/) 为 `mods/<your_mod_id>/` 并阅读 [`docs/MOD_DEVELOPMENT_GUIDE.md`](../docs/MOD_DEVELOPMENT_GUIDE.md)。
2. 使用校验打包脚本生成可复现 ZIP 与 SHA-256：
   ```bash
   python3 scripts/package_mods.py --mods-dir mods --mod <your_mod_id> --output-dir mod-store/packages
   ```
3. 将生成的 `.zip` 发布到你自己的 Release，并在 [`mod-store/submissions/`](../mod-store/submissions/README.md) 提交 `<your_mod_id>.json` PR 即可申请收录进未来 Mod 商城。
