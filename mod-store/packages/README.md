# Mod 商城打包产物暂存说明 (`mod-store/packages/`)

本目录用于开发者在本地运行 `scripts/package_mods.py --output-dir mod-store/packages` 时暂存打包好的 `nebula-mod-<id>-v<version>.zip` 与 `SHA256SUMS.txt`。

> **重要**：`.zip` 归档与临时打包产物已被 `.gitignore` 忽略，**不要提交二进制压缩包到 Git 仓库**；正式发布的 Mod 压缩包统一托管在 **GitHub Releases**，并在 [`../catalog.json`](../catalog.json) 中通过 HTTPS `download_url` + `sha256` 引用。
