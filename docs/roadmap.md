# Roadmap

迭代计划的活动文档。每项含动机、入口文件、实现要点、验收标准。完成的项移到底部 **Done** 区，保留时间戳。

> 每个 P 项的**详细 spec**（含测试样例与测试闭环）见 [`specs/`](./specs/)。密钥处理规范见 [`specs/security-secrets.md`](./specs/security-secrets.md)。

---

## P1 — 三个功能加强重试

**动机**：当前调用 LLM / PubChem / OPSIN 任一外部依赖都可能间歇失败（网络抖、模型返回非法 JSON、PubChem 限流），整次 module 直接 500 或返回空。用户实测要点 2-3 次才稳定。

**思路**：分两层重试，错误类型决定策略。

| 层 | 触发条件 | 策略 |
|---|---|---|
| 外部 HTTP（PubChem / OPSIN web / LLM API） | `httpx.TimeoutException` / 5xx / 429 | 指数退避 3 次，jitter |
| LLM JSON 解析 | `extract_json` 返回 `{}` 但 `raw_text` 非空 | reprompt 1 次，加 "Your previous response was not valid JSON. Return ONLY the JSON object." |

**实现要点**：
- 后端已有 `tenacity>=9.0` 依赖（见 `backend/pyproject.toml`），直接用 `@retry` 装饰器
- 入口：
  - `backend/app/llm/deepseek.py:judge` 等 4 个 provider — 加 `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, json.JSONDecodeError)))`
  - `backend/app/pipeline/naming.py:PubChemIUPACProvider.to_iupac` 和 `OpsinWebProvider.to_smiles` — 同样
- LLM JSON reprompt 单独写一个 `try_parse_or_reprompt(judge, system, user)` helper
- 每次重试在响应里加一个 `judge.retry_count` 字段，前端可见（信息透明）

**验收**：
- 单测：mock httpx 第一次返回 503，第二次 200，整体调用成功
- 真实跑：故意把 `DEEPSEEK_API_KEY` 写错一字，应失败 3 次后才返回错误
- UI 错误率明显下降（粗略观察）

**预估**：半天

---

## P2 — 图片输入 + Gemini Flash 视觉解析

**动机**：化学家工作流里很多分子结构是图（ChemDraw 截图、文献插图、白板拍照），手画完拍一张就能跑分析比敲 SMILES 顺手。

**架构**：
```
Frontend (新增 ImageInput 组件)
   ↓ POST /api/molecule/from_image (multipart/form-data)
Backend ImageOCR provider (Gemini Flash 2.0 vision)
   ↓ 返回 SMILES（或失败）
RoundTripValidator.normalize(smiles)
   ↓ 接入现有 normalize 链
```

**实现要点**：
- 新依赖：`google-generativeai` 已经在 `pyproject.toml` 里（之前给 LLM judge 留的），直接复用
- 新 endpoint：`POST /api/molecule/from_image`，接 `UploadFile`，base64 编码后送到 Gemini Flash
- 提示词强约束："Return ONLY the canonical SMILES for the molecule depicted. If multiple molecules, return them dot-separated. If unsure, return empty string."
- 拿到 SMILES 后**走原来的 normalize 链验证**（PubChem + OPSIN round-trip）——LLM 看错图也能被 round-trip 抓住
- 前端：顶部输入框旁边加一个"📷"小按钮，弹文件选择/拖拽
- 文件大小限制 5MB，类型限 `image/png|jpeg|webp`

**入口文件**：
- 新建 `backend/app/llm/gemini_vision.py`（区别于现有的 `gemini_provider.py`，那个是文本 judge）
- 新建 `backend/app/api/molecule_image.py`
- 前端新建 `frontend/components/ImageInput.tsx`，集成进 `MoleculeInput.tsx`

**验收**：
- 用 PubChem 标准分子结构图（aspirin / ibuprofen）截图测试，准确率应 ≥80%
- 拒绝非分子图（猫照片）应返回空字符串 + 友好错误
- Round-trip 失败的图应在 UI 标 "OCR result not verified" 警告

**预估**：1-2 天（主要时间在 prompt 调参 + 前端 UI 整合）

---

## P3 — UI 中英文切换 + LLM 输出双语

**动机**：用户大多数是中文母语，但 LLM 默认输出英文。

**思路**：两部分独立处理。

### 3a. UI 静态文本 i18n

- 加 `next-intl`（或自己写一个简单 `LanguageContext`，量小不必上库）
- 所有界面文案集中到 `frontend/lib/i18n/{en,zh}.ts`，组件用 `t('key')` 取
- 顶部加语言切换按钮（EN / 中），状态存 localStorage

**入口**：
- 新建 `frontend/lib/i18n/index.ts` + `en.ts` + `zh.ts`
- 改造所有现有组件（约 8 个）的硬编码字符串

### 3b. LLM 输出语言

- Prompt 模板加一个变量 `output_language`：
  - `system.j2` 顶部加 `Respond in {{ output_language }}.`
  - 后端 API 接 `lang` 参数（默认 `en`），传给 prompts.render
- 前端选语言时同时改 API 调用的 `lang` 参数
- **重要**：SMILES / IUPAC / 化学式不翻译（它们是国际标准）；只翻译 `rationale` / `risk` / `disconnection` 这类自然语言字段

**入口**：
- `backend/app/pipeline/prompts/system.j2` 加语言指令
- `backend/app/api/{fga,conditions,retro}.py` 的 Pydantic 模型加 `lang: Literal["en", "zh"] = "en"`
- `backend/app/modules/{fga,conditions,retro}.py` 把 `lang` 传给 prompts.render
- `frontend/lib/api.ts` 所有调用加 `lang` 参数

**验收**：
- 切到中文 → UI 所有标签、按钮、提示变中文 ✓
- 切到中文 → "Analyze functional groups" 返回的 alert 里 `risk` 字段是中文 ✓
- 来回切换 5 次无状态错乱
- LLM cache key 含 `lang`（中英文不共享 cache）

**预估**：1 天

---

## P4 — 公网部署 + 用户自带 API key

**动机**：现在系统只在本地跑，想让别人用就得自己也搭一遍。目标是公网一个 URL，任何人打开网页粘自己的 DeepSeek/OpenAI key 就能用，不消耗作者的 quota。后续如果有真实用户反馈，再决定要不要加持久化数据库。

**关键约束**：
- **RDKit 是 ~150MB 的原生依赖**，**Vercel Functions / Cloudflare Workers / Netlify Functions 等 serverless 跑不了**（包大小限制 50MB，且 Cloudflare Workers 不支持 Python）
- 必须用**容器或 VPS**部署后端

**架构（推荐）**：

```
Frontend (Cloudflare Pages / Vercel — 免费、CDN)
     ↓ /api/* 反代
Backend container (Fly.io / Railway / Render / HF Spaces — 都支持 Docker)
     ↓
PubChem / OPSIN web (外部，免费)
     ↓
LLM API (用户在 UI 里粘的 key，前端转发到后端，后端不存)
```

**实现要点**：

### 4a. 后端容器化
- 新建 `backend/Dockerfile`：基于 `python:3.11-slim`，pip install `.`，CMD `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- 注意 RDKit wheel 在 `linux/amd64` 上是有的，但 ARM Mac 本地 build 要加 `--platform linux/amd64`
- 部署平台选项（按复杂度排）：
  - **Fly.io** — 一个 `fly.toml` 配置 + `fly deploy`，免费档够用，常驻
  - **Railway** — 直接连 GitHub repo 自动部署，按用量收费
  - **HuggingFace Spaces (Docker)** — 完全免费，但有 sleep 机制（48h 不用会休眠，冷启 30s）
  - **Render** — 类似 Railway，免费档 spin-down

### 4b. 用户自带 API key
- 前端加一个 **Settings 抽屉**：粘 `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` 等，存 `localStorage`
- 每次 API 调用通过 HTTP header 转发（避免放 query string 进 access log）：
  ```
  X-User-LLM-Provider: deepseek
  X-User-LLM-API-Key: sk-xxx
  X-User-LLM-Model: deepseek-chat
  ```
- 后端改造 `get_judge_provider()`：优先读 header（per-request），否则 fallback 到环境变量
- **重要**：
  - HTTPS 必须开（防中间人窃听 key）
  - 后端**永远不写 log 不入库**这个 header
  - 加 `CORS` 限定 origin 到自己的前端域名

### 4c. 现有 SQLite cache 的处理
- 容器重启 / 多实例时 SQLite 会**丢缓存**（除非挂 volume）
- 短期：单实例 + Fly.io volume，零成本
- 中期：如果用户量上来 → 换 Postgres / Redis（**等用户反馈再做，不要预先优化**）

### 4d. 用量保护
- 加 rate limit（`slowapi` 包，按 IP），防止匿名用户狂刷耗外部服务额度
- PubChem / OPSIN 的请求要缓存好（已经有了），避免被 IP 封

**入口文件**：
- 新建 `backend/Dockerfile` + `.dockerignore` + `fly.toml`（或对应平台配置）
- 新建 `backend/app/middleware/user_key.py` — 提取 header → request state
- 改 `backend/app/llm/base.py:get_judge_provider()` → 接受 per-request override
- 新建 `frontend/components/SettingsDrawer.tsx`
- 改 `frontend/lib/api.ts` — 注入 header

**验收**：
- 公网 URL 能打开，看到完整 UI
- 不填 key → 三个 tab 都给出 "Please enter your API key in settings" 友好提示
- 填正确 key → 三个 module 完整跑通
- 浏览器 Network 面板检查：key 不出现在 URL / response body
- 切到 `localStorage` 看 key 是否被加密存储（最低限度：不要明文存裸 key，用 Web Crypto 简单 obfuscate 或者干脆不存只用 sessionStorage）

**预估**：2-3 天

### 4e. 数据库（待用户反馈触发）
**条件**：如果上线后看到这些需求，再做。

- 用户希望保存历史分析记录 → 加 user-side IndexedDB（不需要服务端 DB）
- 用户希望分享某个分析结果链接 → 需要服务端持久化，用 Postgres / Supabase
- 用户量大、多实例 → cache 从 SQLite 迁到 Redis

**不要做的事**：上线之前**不要**为了"以后可能要"先加 Postgres / 用户系统 / 鉴权。增加部署复杂度但没有验证过的需求。

---

## Backlog（其他想法）

- [ ] 加 README 顶部 CI / License 徽章
- [ ] 仓库改 public（决定之后）
- [ ] CI 加 `slow` job 跑真实 LLM 调用（需要把 `DEEPSEEK_API_KEY` 放到 GitHub Secrets）
- [ ] Module B 接入开放反应数据库（USPTO / Reaxys mirror）做 candidate retrieval，不再纯靠 LLM 凭空提议
- [ ] Module C 加多步 retrosynthesis 树状图（D3 / React Flow 可视化）
- [ ] PRD §4 的"持续优化 agent"：定期巡检是否有更好的 naming/verification 工具
- [ ] FilterCatalog (PAINS / BRENK / NIH) 作为单独的 safety alerts 通道
- [ ] 一键导出分析结果为 PDF / Markdown 报告
- [ ] 浏览器端历史记录（IndexedDB），不依赖后端 SQLite
- [ ] Playwright E2E 真实跑通三个 tab 的 happy path（不只是 smoke）

---

## Done

- 2026-05-17 — 初始三模块管线（FGA / Conditions / Retro）+ Next.js 前端 + DeepSeek 接入 + GitHub 仓库 + CI 全绿
