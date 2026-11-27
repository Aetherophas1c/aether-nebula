# Aether Nebula Local HTTP API 使用手册（v1.3.1）

本文档说明如何通过 **Aether Nebula 内置的本地自动化 HTTP API**，使用 **Playwright / Puppeteer / Selenium / Python / curl** 编排环境生命周期、查询节点与测速同步时区，并获取受控 Fingerprint-Chromium `158.0.8127.36` 的 CDP 调试端点。

---

## 1. 安全模型与默认行为

- **默认严格关闭**：Aether Nebula 主程序默认**不监听任何本地 HTTP 端口**（PyWebView 通过离线 IPC 通信）。
- **按需显式开启**：在客户端左侧栏点击 **「Local API」**，开启开关并保存后才启动监听，配置持久保存在加密工作区（Vault DB）中。
- **仅绑定回环地址**：固定监听 `127.0.0.1:<port>`，绝不暴露到 `0.0.0.0` 或局域网。
- **防端口指纹扫描**：自动随机分配 `38100 ~ 48999` 范围内的空闲端口；显式禁止使用常见指纹浏览器特征端口（`9222`、`9229`、`50325`、`54345`），且自动避让已被代理占用的端口。
- **强制恒定时间鉴权**：除拒绝全部 `OPTIONS` 预检外，每个请求都必须携带有效 API Key（`hmac.compare_digest` 恒定时间比对），未鉴权直接返回 `401`。
- **零跨域泄露**：响应不附带任何 `Access-Control-Allow-*` 头，固定返回 `Cache-Control: no-store`、`X-Content-Type-Options: nosniff`、`Server: local`，防止访问的网页通过浏览器探针读取本地接口。
- **请求体上限**：JSON 请求体最大 `2 MiB`（`2097152` 字节），且根节点必须为 JSON 对象（`{...}`）。

---

## 2. 鉴权与通用约定

### 2.1 开启并获取地址与 Key
在 Aether Nebula 界面点击左侧栏 **「Local API」**：
1. 打开 **「启用 Local HTTP API」** 开关；
2. 复制页面显示的 **Base URL**（例如 `http://127.0.0.1:41283`）与 **API Key**（格式 `neb_<32位十六进制>`，也可随时点击「轮换 Key」或「随机端口」）；
3. 点击 **「保存并应用」**。

### 2.2 认证请求头（二选一）
```http
Authorization: Bearer neb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
或：
```http
X-API-Key: neb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2.3 统一响应结构
所有接口均返回 UTF-8 JSON：
```json
{
  "ok": true,
  "data": { "...": "..." },
  "error": null
}
```
失败时：
```json
{
  "ok": false,
  "data": null,
  "error": "具体错误说明"
}
```

### 2.4 HTTP 状态码
| 状态码 | 含义 |
| :---: | :--- |
| `200` | 请求成功 |
| `400` | 参数校验失败、JSON 解析错误、环境未绑定代理或业务前置条件不满足 |
| `401` | 缺少或无效的 `Authorization` / `X-API-Key`，或 `OPTIONS` 预检请求 |
| `404` | 路径/方法不存在，或指定的 `profile_id` / `code` 不存在 |
| `500` | 服务内部未预期异常 |

### 2.5 环境标识 `<id_or_code>`
所有单环境路由均支持以下两种标识（路径中需做好 URL 编码）：
- 数字 ID，例如 `1`
- 环境编号 `code`，例如 `ACC-001`

---

## 3. 接口总览

| 方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| `GET` | `/api/v1/status`（别名 `/api/status`） | 健康检查与系统运行状态 |
| `GET` | `/api/v1/groups` | 列出所有环境分组 |
| `POST` | `/api/v1/groups` | 创建环境分组 |
| `GET` | `/api/v1/node-groups` | 列出所有代理节点分组（含节点计数） |
| `POST` | `/api/v1/node-groups` | 创建代理节点分组 |
| `GET` | `/api/v1/nodes` | 列出代理节点脱敏摘要（支持 `?group_id=`，不含原始密钥 URI） |
| `GET` | `/api/v1/profiles` | 分页查询环境列表（支持分组与关键字筛选） |
| `POST` | `/api/v1/profiles` | 创建单个环境，或传入 `count`（`2..200`）批量创建 |
| `GET` | `/api/v1/profiles/<id_or_code>` | 查询单个环境详情与当前运行状态 |
| `PATCH` / `PUT` | `/api/v1/profiles/<id_or_code>` | 更新环境指纹、节点绑定或备注 |
| `DELETE` | `/api/v1/profiles/<id_or_code>` | 删除环境（可选同步清理磁盘数据目录） |
| `POST` | `/api/v1/profiles/open` | 启动或复用环境并返回 CDP 端点（Body 传 `profile_id` 或 `code`） |
| `POST` | `/api/v1/profiles/<id_or_code>/open` | 启动或复用指定环境并返回 CDP 端点（路径传标识） |
| `POST` | `/api/v1/profiles/close` | 优雅关闭运行中的环境（Body 传 `profile_id` 或 `code`） |
| `POST` | `/api/v1/profiles/<id_or_code>/close` | 优雅关闭指定环境（路径传标识） |
| `POST` | `/api/v1/profiles/<id_or_code>/probe` | 经环境专属代理测速，并可选同步 GeoIP 时区与语言 |
| `POST` | `/api/v1/profiles/<id_or_code>/footprint` | 为已停止的环境离线生成真实 Chromium 158 浏览历史、书签与快捷方式 |

---

## 4. 接口详细说明

### 4.1 系统状态
`GET /api/v1/status`（兼容 `GET /api/status`）

返回工作区挂载状态、版本号（`app_version`）、Xray/Mihomo 网关状态、运行中环境计数及 Chromium 路径就绪状态。

```bash
curl -sS -H "Authorization: Bearer $NEBULA_KEY" \
  "$NEBULA_URL/api/v1/status"
```

---

### 4.2 分组管理
- **`GET /api/v1/groups`**：返回所有分组列表。
- **`POST /api/v1/groups`**：创建新分组。

请求体：
```json
{
  "name": "美区自动化",
  "color": "#C96442"
}
```
- `name`（必填）：分组名称。
- `color`（可选）：十六进制颜色字符串，默认 `#3b82f6`。

---

### 4.3 代理节点列表（脱敏）
`GET /api/v1/nodes`

出于安全隔离原则，Local API 仅返回节点调度所需的脱敏摘要字段，**绝不返回**节点明文密码、UUID 或原始代理 URI：
```json
{
  "ok": true,
  "data": [
    {
      "id": 3,
      "name": "US-West-Reality",
      "protocol": "vless",
      "host": "us.example.net",
      "port": 443,
      "last_ip": "198.51.100.25",
      "last_country": "US",
      "last_city": "Los Angeles",
      "last_timezone": "America/Los_Angeles",
      "last_latency_ms": 138
    }
  ],
  "error": null
}
```

---

### 4.4 查询环境列表
`GET /api/v1/profiles`

Query 参数：
| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- |
| `group_id` | int | 空 | 按分组 ID 筛选 |
| `search` | string | `""` | 按编号、名称、备注或节点关键字模糊检索 |
| `page` | int | `1` | 页码（从 1 开始） |
| `page_size` | int | `50` | 每页数量 |

---

### 4.5 创建环境（单个 / 批量）
`POST /api/v1/profiles`

请求体常用字段（未填项自动生成安全默认值、无冲突本地端口与唯一指纹种子）：
| 字段 | 类型 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- |
| `count` | int | `1` | `1` 为单个创建；`2 ~ 200` 为批量创建（每项自动分配唯一 `code`、`local_port` 与 `fingerprint_seed`） |
| `code` | string | 自动递增 | 仅单个创建有效；手动编号若在磁盘已有残余目录将被拒绝防串号 |
| `name` | string | `""` | 环境名称（批量创建时自动追加 `-1`、`-2` 后缀） |
| `group_id` | int \| null | `null` | 所属分组 ID |
| `node_id` | int \| null | `null` | 绑定的代理节点 ID（不绑节点默认禁止启动，除非显式传 `allow_direct=true`） |
| `platform` | string | 宿主机 OS | 伪装操作系统：`"windows"` / `"macos"` / `"linux"` |
| `browser_brand` | string | `"chrome"` | 浏览器品牌：`"chrome"` / `"edge"` / `"opera"` / `"vivaldi"` |
| `brand_version` | string | `""` | 可选自定义品牌版本（Chrome 留空即使用内核内置 `158.0.8127.x`） |
| `cpu_cores` | int | `8` | 逻辑 CPU 核数（`1 ~ 96`） |
| `memory_gb` | int | `8` | 内存容量声明（`deviceMemory` 受 W3C 8GB 上限规范约束） |
| `timezone` | string | `"America/Los_Angeles"` | IANA 时区，配合 `--timezone` 锁死 ICU 与 V8 |
| `lang` | string | `"en-US"` | BCP-47 语言标签，自动同步 `Accept-Language` 与 `navigator.languages` |
| `window_size` | string | `"1366,768"` | 初始窗口尺寸 `"宽,高"` |
| `refresh_rate` | int \| null | `null` | 可选 `requestAnimationFrame` 刷新率节流（`30 ~ 240` Hz） |
| `disable_canvas_audio_noise` | bool / int | `0` | 默认 `0`（开启抗回读重构后的 Canvas/Audio 确定性扰动）；设为 `1`/`true` 可完全关闭 |
| `notes` | string | `""` | 备注说明 |

单个创建示例：
```json
{
  "name": "Shopify-US-01",
  "group_id": 1,
  "node_id": 3,
  "platform": "macos",
  "browser_brand": "chrome",
  "cpu_cores": 8,
  "window_size": "1440,900",
  "timezone": "America/Los_Angeles",
  "lang": "en-US"
}
```

批量创建响应（`count > 1`）：
```json
{
  "ok": true,
  "data": {
    "created": [ { "id": 10, "code": "ACC-010", "..." : "..." } ],
    "count": 5
  },
  "error": null
}
```

---

### 4.6 单环境查询 / 更新 / 删除
- **`GET /api/v1/profiles/<id_or_code>`**：返回单个环境完整记录与运行态（`running`, `pid`, `cdp_port` 等）。
- **`PATCH /api/v1/profiles/<id_or_code>`**（或 `PUT`）：局部更新任意可修改字段（如 `name`, `node_id`, `group_id`, `platform`, `timezone`, `lang`, `notes`, `disable_canvas_audio_noise` 等）；若修改了代理路由字段会自动热重载 Xray/Mihomo。
- **`DELETE /api/v1/profiles/<id_or_code>`**：停止运行中的浏览器并删除数据库记录。
  - 可选参数 `delete_data_dir`（别名 `delete_files`，支持放在 Query `?delete_data_dir=true` 或 JSON Body `{"delete_data_dir": true}`），默认 `false`；设为 `true` 时同步清除 `{vault_root}/profiles/<code>` 磁盘目录。

---

### 4.7 启动环境并获取 CDP 端点（核心自动化接口）
- `POST /api/v1/profiles/<id_or_code>/open`
- 或 `POST /api/v1/profiles/open`（Body 中提供 `profile_id` 或 `code`）

请求体参数：
| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- |
| `profile_id` / `code` | int / string | — | 仅 `/api/v1/profiles/open` 需要 |
| `cdp` | bool | `true` | 是否分配独占的 `127.0.0.1` 临时 CDP 调试端口 |
| `headless` | bool | `false` | 是否以 `--headless=new` 无头模式运行 |
| `start_url` | string \| null | `null` | 初始打开地址（安全限制：仅允许 `about:blank` 或 `https://`） |
| `sync_geo`（别名 `auto_sync_timezone`） | bool | `false` | 启动前是否自动通过代理探测出口 IP 并同步时区/语言 |
| `allow_direct` | bool | `false` | 未绑定代理节点时默认拒绝启动；设为 `true` 才允许本机直连（裸启动） |
| `restart_for_cdp` | bool | `false` | 若该环境先前已在 UI 无调试端口模式下运行，设为 `true` 可自动优雅关闭并带 CDP 重启 |

成功响应示例：
```json
{
  "ok": true,
  "data": {
    "launched": true,
    "already_running": false,
    "profile_id": 1,
    "pid": 52104,
    "code": "ACC-001",
    "started_at": "2026-11-26T12:00:00+00:00",
    "cdp_port": 51842,
    "http_endpoint": "http://127.0.0.1:51842",
    "ws_endpoint": "ws://127.0.0.1:51842/devtools/browser/8f7c...",
    "browser_version": "Chrome/158.0.8127.36",
    "local_proxy": "socks5://127.0.0.1:20001",
    "webdriver_path": "/path/to/bin/chromium/chromedriver",
    "direct_mode": false
  },
  "error": null
}
```

> **提示**：若该环境已经在带 CDP 模式下运行，再次调用 `open` 会直接幂等返回当前 `pid`、`cdp_port`、`http_endpoint` 与 `ws_endpoint`（`already_running: true`），不会重复拉起窗口。

---

### 4.8 优雅关闭环境
- `POST /api/v1/profiles/<id_or_code>/close`
- 或 `POST /api/v1/profiles/close`（Body 中提供 `profile_id` 或 `code`）

会先发送 `WM_CLOSE`（Windows）或 `SIGTERM`（macOS/Linux）让 Chromium 完整刷盘保存 Cookie/LocalStorage SQLite 数据库，超时后再兜底结束进程。

---

### 4.9 出口测速与 GeoIP 时区同步
`POST /api/v1/profiles/<id_or_code>/probe`

请求体：
```json
{
  "sync_timezone": true
}
```
经该环境绑定的专属本地 SOCKS5 代理请求 `ip_check_url`，返回出口 IP、国家/城市、延迟与时区；`sync_timezone` 默认为 `true`，会自动将探测到的时区与推荐语言回写到该环境配置。

---

### 4.10 离线生成浏览痕迹（历史 / 书签 / 新标签页快捷方式）
`POST /api/v1/profiles/<id_or_code>/footprint`

仅允许对**已关闭**的环境执行（防止 Chromium SQLite 锁冲突）。自动根据该环境的 `lang` 与 `timezone` 匹配区域站点池与当地昼夜活跃曲线，生成精确兼容 Chromium `158.0.8127.36` 的 `History`（`v70`）、`Top Sites`（`v5`）、`Bookmarks`（含合法 MD5 校验和）及 `Preferences`：

```json
{
  "style": "dev",
  "intensity": "standard",
  "days": 30,
  "include_history": true,
  "include_bookmarks": true,
  "include_shortcuts": true,
  "mode": "append"
}
```
- `style`：`"general"` | `"dev"` | `"ai"` | `"commerce"`
- `intensity`：`"light"` | `"standard"` | `"rich"`
- `days`：`1 ~ 180`（默认 `30`）
- `mode`：`"append"`（追加，默认）| `"replace"`（重建）

---

## 5. 自动化接管代码示例

### 5.1 curl 快速联调
```bash
export NEBULA_URL="http://127.0.0.1:41283"
export NEBULA_KEY="neb_replace_with_your_key"

# 1. 启动 ACC-001 并获取 CDP 端点
curl -sS -X POST "$NEBULA_URL/api/v1/profiles/ACC-001/open" \
  -H "Authorization: Bearer $NEBULA_KEY" \
  -H "Content-Type: application/json" \
  -d '{"cdp": true, "sync_geo": true}'

# 2. 用完后优雅关闭
curl -sS -X POST "$NEBULA_URL/api/v1/profiles/ACC-001/close" \
  -H "Authorization: Bearer $NEBULA_KEY"
```

### 5.2 Python + Playwright（推荐）
```python
import httpx
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:41283"
HEADERS = {"Authorization": "Bearer neb_replace_with_your_key"}
PROFILE_CODE = "ACC-001"

# 1. 通过 Local API 启动指纹浏览器
resp = httpx.post(
    f"{BASE_URL}/api/v1/profiles/{PROFILE_CODE}/open",
    headers=HEADERS,
    json={"cdp": True, "headless": False, "restart_for_cdp": True},
    timeout=30.0,
).json()
assert resp["ok"], resp["error"]
ws_endpoint = resp["data"]["ws_endpoint"]

# 2. 接管 CDP 会话
try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://example.com", wait_until="domcontentloaded")
        print("Title:", page.title())
        browser.close()
finally:
    # 3. 优雅关闭环境确保 Cookie 落盘
    httpx.post(f"{BASE_URL}/api/v1/profiles/{PROFILE_CODE}/close", headers=HEADERS, timeout=15.0)
```

### 5.3 Node.js + Puppeteer
```javascript
import puppeteer from 'puppeteer-core';

const BASE_URL = 'http://127.0.0.1:41283';
const HEADERS = {
  'Authorization': 'Bearer neb_replace_with_your_key',
  'Content-Type': 'application/json',
};

const openRes = await fetch(`${BASE_URL}/api/v1/profiles/ACC-001/open`, {
  method: 'POST',
  headers: HEADERS,
  body: JSON.stringify({ cdp: true }),
}).then(r => r.json());

if (!openRes.ok) throw new Error(openRes.error);

const browser = await puppeteer.connect({
  browserWSEndpoint: openRes.data.ws_endpoint,
  defaultViewport: null,
});

try {
  const [page] = await browser.pages();
  await page.goto('https://example.com', { waitUntil: 'domcontentloaded' });
  console.log('Title:', await page.title());
} finally {
  browser.disconnect();
  await fetch(`${BASE_URL}/api/v1/profiles/ACC-001/close`, {
    method: 'POST',
    headers: HEADERS,
  });
}
```

### 5.4 Python + Selenium（使用内置匹配的 `chromedriver`）
```python
import httpx
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

BASE_URL = "http://127.0.0.1:41283"
HEADERS = {"Authorization": "Bearer neb_replace_with_your_key"}

open_res = httpx.post(
    f"{BASE_URL}/api/v1/profiles/ACC-001/open",
    headers=HEADERS,
    json={"cdp": True},
    timeout=30.0,
).json()
assert open_res["ok"], open_res["error"]

data = open_res["data"]
opts = Options()
opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{data['cdp_port']}")

driver = webdriver.Chrome(
    service=Service(executable_path=data["webdriver_path"]),
    options=opts,
)
try:
    driver.get("https://example.com")
    print("Title:", driver.title)
finally:
    driver.quit()
    httpx.post(f"{BASE_URL}/api/v1/profiles/ACC-001/close", headers=HEADERS, timeout=15.0)
```

---

## 6. 常见问题

1. **为什么启动时报错「已在无调试端口模式下运行」？**
   用户在桌面 UI 手动点「打开」时默认以零 CDP 端口的纯净模式启动。自动化脚本若需要接管该环境，可在请求体中传 `"restart_for_cdp": true` 自动优雅重启为 CDP 模式，或先调用 `/close`。
2. **为什么开启 CDP 后不会被网站检测 `Runtime.enable`？**
   Aether Nebula 自编译的 Chromium `158.0.8127.36` 已内置补丁 `002-disable-runtime-enable.patch` 与 `003` 的 `navigator.webdriver=false` 处理，在保留正常 CDP 自动化能力的同时中和了经典的 `Runtime.enable` 侧信道检测。
3. **跨设备启动环境会字体乱码或暴露宿主字体吗？**
   不会。通过 Local API 启动的环境同样由 `BrowserLauncher` 注入 `--fingerprint-font-dir`，自动按环境的 `platform`（Windows / macOS / Linux）私有加载对应开源字体包，与桌面 UI 手动启动行为 100% 一致。
