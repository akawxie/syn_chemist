# P4 — 公网部署 + 用户自带 API key Spec

## 1. 目标

公网一个 URL，任何人打开网页粘自己的 API key 就能用三个模块，不消耗作者的 LLM quota。仓库目前已是 public，部署后可作为 demo 直接演示。

**非目标**（暂不做）：
- 用户账号系统 / 鉴权登录
- 历史记录持久化到服务端
- 多用户协作

---

## 2. 关键约束

| 约束 | 后果 |
|---|---|
| **RDKit 是 ~150MB 原生依赖** | Vercel Functions / Cloudflare Workers / Netlify Functions 全部不行（包大小限制 50MB） |
| **OPSIN 是 Java 依赖** | 我们已通过 OPSIN web API 规避，不需要本地 Java |
| **PubChem / OPSIN 有速率限制** | 必须保留服务端缓存 |
| **LLM key 极敏感** | 后端必须**永不**入库 / 入日志 |

→ 后端必须**容器部署**到支持长进程的平台。

---

## 3. 架构

```
                            ┌───────────────────────┐
                            │  Cloudflare Pages /   │
                            │  Vercel (Frontend)    │
                            │  - 免费 CDN           │
                            │  - 用户在 Settings    │
                            │    抽屉粘 API key     │
                            │  - localStorage 存    │
                            └───────────┬───────────┘
                                        │ HTTPS only
                                        │ /api/* → 后端
                                        │ X-User-LLM-API-Key: sk-xxx
                                        │ X-User-LLM-Provider: deepseek|openai|gemini
                                        ▼
                            ┌───────────────────────┐
                            │  Backend Container    │
                            │  Fly.io (推荐)        │
                            │  - Docker             │
                            │  - 1 instance + vol   │
                            │  - SQLite cache 挂卷  │
                            │  - slowapi rate limit │
                            └───────────┬───────────┘
                                        │
                          ┌─────────────┼─────────────┐
                          ▼             ▼             ▼
                       PubChem        OPSIN       LLM API
                       (free)         (free)      (user key)
```

### 3.1 平台选型

| 平台 | 优点 | 缺点 | 用途 |
|---|---|---|---|
| **Fly.io** | 一个 fly.toml；免费档 256MB×3；常驻；有 volume | 信用卡验证 | **后端首选** |
| Railway | GitHub 直连自动部署 | 免费试用后按量收费 | 后端备选 |
| Hugging Face Spaces (Docker) | 完全免费 | 48h 不用休眠，冷启 30s | 后端 demo 用 |
| Render | 类似 Railway | 免费档 spin-down | 后端备选 |
| **Cloudflare Pages** | 静态前端免费 CDN 全球 | 仅静态 | **前端首选** |
| Vercel | Next.js 原生 | — | 前端备选 |

### 3.2 用户自带 key 流转

```
[Settings 抽屉] 用户粘 sk-xxx
       ↓
[localStorage] 存为 `ai_chemist_llm_keys` (JSON: {deepseek:..., openai:..., gemini:...})
       ↓ 每次 API 调用
[fetch() in lib/api.ts] 注入 header X-User-LLM-API-Key / X-User-LLM-Provider
       ↓
[后端 middleware] 读 header → 写入 request.state.user_llm_key
       ↓
[modules/*.py 调用 get_judge_provider(request)] 优先用 request.state.user_llm_key
       ↓
[provider.judge()] 执行调用，**结束后立刻 del key 局部变量**
       ↓
[response] 返回结果，key 不出现在 body
```

**禁止事项**（在代码 review 时检查）：
- ❌ `logger.info(f"using key {key}")` —— 任何 logger 调用包含 key 变量
- ❌ key 进 query string —— 会进 access log
- ❌ key 进 response body —— 即使 echo 也不行
- ❌ key 进 cache key —— SQLite 会持久化
- ❌ key 通过 GET URL 传 —— browser history + referrer 都会有

---

## 4. 入口文件

### 4.1 后端

| 文件 | 改动 |
|---|---|
| `backend/Dockerfile` (新建) | `python:3.11-slim`，pip install `.`，`CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` |
| `backend/.dockerignore` (新建) | 排除 `.env`, `*.db`, `tests/`, `__pycache__` |
| `fly.toml` (新建) | app name, region, volume mount `/data` 给 SQLite |
| `backend/app/middleware/user_key.py` (新建) | 提取 `X-User-LLM-*` headers → `request.state` |
| `backend/app/llm/base.py` | `get_judge_provider(request)` 接 request；优先读 state |
| `backend/app/main.py` | 注册 middleware；加 CORS 白名单（生产 = 自己前端域名）；加 `slowapi` rate limiter |
| `backend/app/api/*.py` | endpoint 签名加 `request: Request`，透传 |
| `backend/pyproject.toml` | 加 `slowapi` |
| `backend/app/config.py` | 加 `frontend_origin: str` 用于 CORS；`rate_limit: str = "30/minute"` |

### 4.2 前端

| 文件 | 改动 |
|---|---|
| `frontend/components/SettingsDrawer.tsx` (新建) | 抽屉 UI；4 个 provider 各一个 input + 显示/隐藏 toggle |
| `frontend/lib/keys.ts` (新建) | localStorage 读写封装；`getKey(provider)`, `setKey(...)`, `clearAll()` |
| `frontend/lib/api.ts` | 所有 fetch 加 header 注入；`NEXT_PUBLIC_API_BASE` 切换本地 / 生产 |
| `frontend/components/{tabs}/*.tsx` | 调用前检查 key 是否配；未配显示 "请在 Settings 中配置 API key" |
| `frontend/app/layout.tsx` | 头部加齿轮图标打开 Settings |
| `frontend/next.config.mjs` | 生产 build 时 `/api/*` 反代到 `process.env.NEXT_PUBLIC_API_BASE` |

### 4.3 仓库根

| 文件 | 改动 |
|---|---|
| `.github/workflows/deploy.yml` (新建) | push to main → `flyctl deploy`；Cloudflare Pages 自动 watch |
| `README.md` | 加 "Deploy your own" 一节 |
| `docs/specs/security-secrets.md` | 已存在；引用其密钥处理规范 |

---

## 5. 测试样例

### 5.1 后端单元（mock，无网络）

`backend/tests/test_user_key_middleware.py`

| 用例 | 输入 | 期望 |
|---|---|---|
| `test_header_extraction` | request 带 `X-User-LLM-API-Key: sk-test` + `X-User-LLM-Provider: deepseek` | `request.state.user_llm_key == "sk-test"`, `request.state.user_llm_provider == "deepseek"` |
| `test_missing_header_falls_back_env` | request 无 header，env 有 `DEEPSEEK_API_KEY=sk-env` | provider 用 env key |
| `test_no_header_no_env_returns_friendly_error` | request 无 header，env 也清空 | API 返回 400 + `{"error": "no_api_key", "message": "Configure API key in Settings"}` |
| `test_invalid_provider_rejected` | `X-User-LLM-Provider: hackerprovider` | 400 |
| `test_key_not_in_response_body` | 任一成功请求 | response body JSON 序列化后 grep `sk-` 应为空 |
| `test_key_not_in_logs` | 任一成功请求 | 捕获 logger 输出 grep `sk-` 应为空 |

### 5.2 后端集成（容器）

`backend/tests/integration/test_container.sh`（手动跑）

```bash
# 1. 本地 build
docker build -t ai-chemist-be backend/
# 2. 起容器
docker run --rm -p 8001:8000 -e PORT=8000 ai-chemist-be &
# 3. health check
curl -f http://localhost:8001/api/health
# 4. 无 key
curl -X POST http://localhost:8001/api/fga -d '{"input":"CCO"}' -H "Content-Type: application/json"
# → 应返回 400 "no_api_key"
# 5. 带 key
curl -X POST http://localhost:8001/api/fga \
  -H "X-User-LLM-API-Key: $DEEPSEEK_API_KEY" \
  -H "X-User-LLM-Provider: deepseek" \
  -H "Content-Type: application/json" \
  -d '{"input":"CCO"}'
# → 应正常返回
```

### 5.3 端到端（上线后冒烟）

`frontend/tests/e2e/deployment.spec.ts`（指向公网 URL）

| 用例 | 期望 |
|---|---|
| `test_homepage_loads` | 公网 URL 200，Lighthouse score > 80 |
| `test_no_key_shows_setup_prompt` | 清 localStorage 后访问 → 看到 "Configure API key" 提示 |
| `test_with_key_runs_fga` | 配 key → 跑 aspirin → 看到结果 |
| `test_key_not_in_network_tab` | DevTools Network 检查：所有请求的 URL 和 response body 都不含 `sk-` |
| `test_rate_limit_kicks_in` | 用 script 1 分钟内打 35 次 `/api/fga` → 第 31 次开始返回 429 |
| `test_cors_blocks_other_origin` | 从 `https://evil.example.com` 模拟 fetch 调 API → CORS 拒绝 |

### 5.4 安全审计 checklist（人工，发布前）

- [ ] grep `git log --all -p -S 'sk-'`：commit 历史无任何 key
- [ ] grep `git log --all -p -S 'AIza'`：同上
- [ ] `docker history ai-chemist-be | grep -i key`：镜像层无 key
- [ ] 访问 https://your-app.fly.dev/api/health 应 200；访问 https://your-app.fly.dev/.env 应 404
- [ ] 把 key 故意带在 URL `?api_key=sk-x` 调用 → 后端应忽略并按"无 key"流程
- [ ] HTTPS 强制：`http://your-app...` 应 301 到 https
- [ ] CSP header 已设（防 XSS 盗 localStorage 里的 key）
- [ ] localStorage 中 key 即使被 XSS 盗，受害面仅限"该用户的 LLM quota"——不持久化在服务端

详细密钥处理规范见 [security-secrets.md](./security-secrets.md)。

---

## 6. 测试闭环

```
PR commit
  → CI（GitHub Actions）
    → pytest -m "not slow"
    → docker build（健康检查 Dockerfile 没坏）
    → frontend typecheck + build
  ↓ merge to main
  → deploy.yml
    → flyctl deploy（后端）
    → Cloudflare Pages 自动 build & deploy（前端）
  → 部署后冒烟
    → curl /api/health 200
    → Playwright 跑 5.3 公网用例
  → 发布前安全审计 5.4 人工 checklist
```

**绿灯条件**：
1. CI 全绿
2. 容器测试 5.2 全过
3. 公网冒烟 5.3 全过
4. 安全审计 5.4 全打勾

---

## 7. 验收标准

**功能**：
- [ ] 公网 URL 能打开，HTTPS 自动
- [ ] 不配 key → 三个 tab 都给出友好引导
- [ ] 配 key → 三个 module 完整跑通
- [ ] Rate limit 生效（30/分钟/IP）

**安全**：
- [ ] DevTools Network 面板：key 不在 URL / response body / 任何 echo 字段
- [ ] 后端日志：grep `sk-` 与 `AIza` 均无命中
- [ ] commit history：grep 同上无命中（见 [security-secrets.md](./security-secrets.md)）
- [ ] CORS 限定到自己前端域名
- [ ] CSP header 配置正确

**运维**：
- [ ] Fly volume 挂载 `/data`，SQLite cache 重启不丢
- [ ] README 有 "如何自己部署一份" 步骤
- [ ] 监控：Fly metrics 看 5xx 率

**预估工时**：2–3 天（Dockerfile + Fly 配置半天，前端 Settings 半天，安全审计与冒烟半到一天，调 CORS / CSP / rate limit 半天）
