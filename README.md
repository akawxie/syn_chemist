# AI_chemist

AI 辅助的合成化学工作流。**核心差异**：不训练化学领域大模型，而是把通用 LLM（DeepSeek / GPT / Claude / Gemini）当作 **judge + filter**，让开源化学计算工具（RDKit / OPSIN / PubChem / STOUT）承担"事实判定"。

> 设计前提：通用 LLM 对"判断一个方案是否合理"准确率约 80%，但对"从零生成方案"很差。所以管线是 **generate → judge → verify**：LLM 评判与排序，工具做事实验证。

---

## 1. 系统原理

```
   ┌────────────┐    ┌──────────────────────┐    ┌──────────────────┐    ┌───────────────────┐    ┌──────────────────┐
   │  Structured│    │  Naming round-trip   │    │  Prompt template │    │  LLM judgment     │    │ RDKit verify     │
   │  input     │──▶ │  SMILES → IUPAC →    │──▶ │  per module      │──▶ │  (DeepSeek/GPT/   │──▶ │ structure /       │
   │  (SMILES,  │    │  SMILES 闭环比对     │    │  (Jinja2)        │    │  Claude/Gemini)   │    │ atom balance /    │
   │  InChI)    │    │                      │    │                  │    │                   │    │ SMARTS match     │
   └────────────┘    └──────────────────────┘    └──────────────────┘    └───────────────────┘    └──────────────────┘
                                                                                                          │
                                                                                                          ▼
                                                                                              ┌───────────────────────┐
                                                                                              │ Composite confidence  │
                                                                                              │ = w₁·round_trip       │
                                                                                              │ + w₂·judge_self_conf  │
                                                                                              │ + w₃·verify_pass_rate │
                                                                                              └───────────────────────┘
```

**三条不可破的设计规则**

1. **LLM 是 judge / filter，不是事实来源**。任何 LLM 产出都要被 RDKit 反向验证。
2. **能闭环检查就闭环检查**。SMILES↔IUPAC 是典型例子：PubChem 把 SMILES 翻译成 IUPAC，OPSIN 再把 IUPAC 反译回 SMILES，与原 canonical SMILES 比对。
3. **Confidence 是一等输出字段**，由三个分量加权：round-trip 命中、LLM 自信度、RDKit 验证通过率。

---

## 2. 功能模块

| 模块 | 入口 API | 说明 |
|---|---|---|
| **A · Functional Group Alert** | `POST /api/fga` | RDKit 抽取 25 条危险基团 SMARTS + 85 个 `fr_*` fragment → LLM 评估每项实操风险 → 允许 LLM 补充并提供 SMARTS → RDKit 反验 |
| **B · Reaction Conditions** | `POST /api/conditions` | LLM 提议候选条件（溶剂/催化剂/温度/时间/当量）→ RDKit 做反应物/产物的合法性 + 重原子守恒（advisory）→ 按 verify 通过率排序 |
| **C · Retrosynthesis** | `POST /api/retro` | LLM 提出宏观逆合成路线 + 中间体 SMILES → RDKit 检查每个中间体的化学合法性 → 多候选路线返回 |

辅助端点：`POST /api/molecule/normalize` 跑独立的 SMILES↔IUPAC 闭环，不调用 LLM。

---

## 3. 技术栈

| 层 | 工具 |
|---|---|
| Backend | Python 3.11 · FastAPI · Uvicorn · Pydantic v2 · SQLModel · Jinja2 |
| 化学层 | RDKit 2024+（结构合法性 / SMARTS / Fragments 模块） |
| Naming round-trip | **PubChem REST**（SMILES→IUPAC，免费免 key）· **OPSIN web service**（IUPAC→SMILES，EBI 提供）· 可插拔的 STOUT（如有 Python 3.9 + TF 2.10 环境） |
| LLM judge | DeepSeek (默认，OpenAI-compatible) · OpenAI · Anthropic · Google Gemini |
| Cache | SQLite，缓存 LLM / PubChem / OPSIN 调用，可序列化 dataclass |
| Frontend | Next.js 14 (App Router) · React 18 · TypeScript · Tailwind CSS · smiles-drawer (SVG) |
| Test | pytest · pytest-asyncio · Playwright (E2E) |

**Naming 层是 strategy 模式**：`IUPACProvider` / `OPSINProvider` 协议定义在 `backend/app/pipeline/naming.py`，目前提供 PubChem / STOUT / Chained / Stub 几个实现，新工具只需实现一个 protocol 就能挂进来。

---

## 4. 仓库布局

```
AI_chemist/
├── PRD.md                          产品需求（最初的设计源头）
├── CLAUDE.md                       Claude Code 协作约束
├── backend/
│   ├── pyproject.toml
│   ├── .env                        本地配置（API key / provider 选择）
│   ├── data/ai_chemist.db          SQLite 缓存数据库（自动生成）
│   └── app/
│       ├── main.py                 FastAPI 应用 + 4 个 router
│       ├── config.py               Settings（pydantic-settings）
│       ├── cache.py                SQLite 缓存 + dataclass 序列化
│       ├── db.py                   SQLModel schema
│       ├── api/                    路由层（4 个端点）
│       ├── llm/                    JudgeProvider ABC + 4 个 provider 实现
│       ├── modules/                A/B/C 三个业务模块
│       └── pipeline/
│           ├── naming.py           SMILES↔IUPAC 闭环 + 多 provider
│           ├── verify.py           RDKit 检查 + SMARTS 表 + fr_* 清单
│           ├── confidence.py       三分量加权 composite
│           └── prompts/            Jinja2 模板（system/fga/conditions/retro）
├── frontend/
│   ├── package.json
│   ├── next.config.mjs             /api/* 反向代理到 :8000
│   ├── app/                        App Router 入口
│   ├── components/                 通用组件 + tabs/{FGA,Conditions,Retro}Tab
│   └── lib/                        types + api 客户端
└── docs/
```

---

## 5. 部署 / 启动

### 5.1 一次性安装

**前置**：macOS / Linux · Python 3.11（不要用 3.12+，RDKit 兼容性最稳的版本）· Node 18+ · Java 不需要（OPSIN 走 web）。

**Backend**

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -e .
```

> 安装 STOUT-pypi 在大多数现代环境上会失败（它锁死 `tensorflow==2.10.1`），本项目 **默认走 PubChem + OPSIN web** 作为 IUPAC 通路，效果对常见有机分子完全够用。如果你确实需要本地 STOUT，要单独建一个 Python 3.9 + TF 2.10 的旁路环境。

**Frontend**

```bash
cd ../frontend
npm install
```

### 5.2 配置 `.env`

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入自己的 API key
```

`.env` 已在 `.gitignore` 中，不会被误提交。完整字段参考 `backend/.env.example`，最关键的是：

```ini
JUDGE_PROVIDER=deepseek                       # deepseek | openai | anthropic | gemini
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx  # 在 https://platform.deepseek.com/api_keys 申请
IUPAC_PROVIDER=pubchem_stout                  # PubChem 命中先，STOUT 兜底
OPSIN_PROVIDER=opsin_web
OPSIN_WEB_URL=https://www.ebi.ac.uk/opsin/ws
```

> 配置文件加载用绝对路径（见 `backend/app/config.py`），所以从任何 cwd 启动 uvicorn 都能找到 `.env`。

### 5.3 启动后端（带 `--reload`）

```bash
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

`--reload` 让 uvicorn watchgod 监听 Python 源码，**改代码后自动重启进程**。模板文件（`*.j2`）由 Jinja2 自己热加载，不需要重启。

可访问的端点：
- `http://127.0.0.1:8000/docs` — OpenAPI / Swagger UI
- `http://127.0.0.1:8000/api/...` — 4 个业务端点

### 5.4 启动前端

```bash
cd frontend
npm run dev
```

打开 `http://localhost:3000`。Next.js 通过 `next.config.mjs` 把 `/api/*` 反代到 `127.0.0.1:8000`，避免 CORS 配置。

### 5.5 macOS 权限提示

如果在 macOS 看到 "Operation not permitted" 访问 `Documents/...` 下的 venv：去 **System Settings → Privacy & Security → Full Disk Access**，把你的 Terminal（或 iTerm）加入并打开，**完全退出 Terminal 再重开**。

---

## 6. 使用说明

### 6.1 UI

打开 `http://localhost:3000`，顶部输入框接受 **SMILES** 或 **InChI**。输入会在 400ms 防抖后调用 `/api/molecule/normalize`，结果显示在下方：

- `canonical:` RDKit 计算的规范 SMILES
- `IUPAC:` PubChem 返回的系统命名
- `round-trip:` `ok`（闭环成功，1.0 分）/ `partial (xx%)`（任一步失败的降级评分）
- 右侧分子结构图（smiles-drawer 在 dark 主题下渲染 SVG）

下方三个 tab：

| Tab | 输入 | 输出 |
|---|---|---|
| Functional Groups | 共用顶部分子 | `detected_groups`（25 条危险 SMARTS 命中）· 可折叠的 fragment inventory（`fr_*` 全量）· LLM alerts（每条带 severity / risk / 可选 smarts）· RDKit verify 详情 |
| Reaction Conditions | reactant + product + 可选 reaction_class_hint | 候选条件表（solvent/catalyst/temp/time/equiv/score）+ rationale |
| Retrosynthesis | 单个 target | 多条候选路线，每条含 disconnection / intermediates（每个画图）/ steps |

所有结果块右上角都有 **confidence 徽章**——点开看 round-trip / judge / verify 三个分量。

### 6.2 直接调 API

**Normalize**
```bash
curl -s -X POST http://127.0.0.1:8000/api/molecule/normalize \
  -H "Content-Type: application/json" \
  -d '{"input":"CC(=O)Oc1ccccc1C(=O)O"}'
```
返回：
```json
{
  "input_raw": "CC(=O)Oc1ccccc1C(=O)O",
  "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "iupac": "2-acetyloxybenzoic acid",
  "round_trip_ok": true,
  "round_trip_score": 1.0,
  "notes": []
}
```

**Functional Group Alert**
```bash
curl -s -X POST http://127.0.0.1:8000/api/fga \
  -H "Content-Type: application/json" \
  -d '{"input":"CCO"}'
```

**Reaction Conditions**
```bash
curl -s -X POST http://127.0.0.1:8000/api/conditions \
  -H "Content-Type: application/json" \
  -d '{"reactant":"CCO","product":"CC=O","reaction_class_hint":"oxidation"}'
```

**Retrosynthesis**
```bash
curl -s -X POST http://127.0.0.1:8000/api/retro \
  -H "Content-Type: application/json" \
  -d '{"target":"CC(C)Cc1ccc(C(C)C(=O)O)cc1"}'
```

### 6.3 切换 LLM provider

只改 `.env`（无需改代码）：

```ini
JUDGE_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-7
```

四个 provider 抽象在 `backend/app/llm/`：DeepSeek（OpenAI compatible）· OpenAI · Anthropic · Gemini。Provider 切换 → uvicorn 自动 reload（如带 `--reload`）→ 立即生效。

### 6.4 调整 confidence 权重

`.env` 可选项：
```ini
CONFIDENCE_WEIGHT_ROUND_TRIP=0.3
CONFIDENCE_WEIGHT_JUDGE=0.3
CONFIDENCE_WEIGHT_VERIFY=0.4
```

### 6.5 清缓存

LLM 调用、PubChem、OPSIN 都按 namespace 缓存到 `data/ai_chemist.db`。手工清掉某类：

```bash
cd backend
.venv/bin/python -c "
import sqlite3
c = sqlite3.connect('data/ai_chemist.db')
c.execute(\"DELETE FROM cache_entry WHERE namespace LIKE 'judge:%'\")
c.commit()
print('cleared:', c.total_changes)
"
```

---

## 7. 测试

```bash
cd backend
.venv/bin/pytest                              # 单测 + 集成
.venv/bin/pytest -m slow                      # 真实 STOUT/OPSIN/LLM（默认跳过）

cd ../frontend
npm run typecheck
npx playwright test tests/e2e/smoke.spec.ts   # 浏览器端 E2E
```

---

## 8. 已知边界 / 后续

- **STOUT 本地化跑不通**（依赖 TF 2.10），用 PubChem 替代是务实选择，但极少见或全新结构 PubChem 没有就只能 stub。如果需要 100% 覆盖，建一个 py3.9 + TF 旁路服务。
- **Module B 没接开放反应数据库**（PRD 提到的 USPTO/Reaxys），目前完全靠 LLM 提议条件。后续可加 candidate retrieval 层。
- **PRD §4 的"持续优化 AI agent"** 没实现——定期巡检看是否有更好的 naming/verification 工具。
- **OPSIN 对某些方括号嵌套的 IUPAC 名称解析失败**，导致 round-trip 拿不到满分。这是真实信号（命名链有缺口），不是 bug；只会让 composite confidence 降一些。

---

## 9. 故障排查

| 现象 | 原因 | 修复 |
|---|---|---|
| `/api/fga` 返回 500，traceback 提 `StrictUndefined` | `fga.py` 改了但 uvicorn 没 reload | 加 `--reload` 启动，或 Ctrl+C 重启 |
| `IUPAC: —` 一直为空 | `.env` 里 `IUPAC_PROVIDER=stub` 或 PubChem 服务不可达 | 改为 `pubchem_stout`，重启 |
| `'str' object has no attribute 'parsed'` | 老版本 cache 序列化把 dataclass 转成了 repr 字符串 | `backend/app/cache.py` 已修；清空 `data/ai_chemist.db` 的 `cache_entry` 表 |
| `Operation not permitted` 访问 venv | macOS TCC 拦截 | Privacy & Security → Full Disk Access 授权 Terminal |
| 启动报 `tensorflow==2.10.1` 找不到 | STOUT 装不上 | 跳过 `pip install -e ".[stout]"`，用默认 PubChem 通路 |
| 后端 `/docs` 200 但业务端点报错 | 多半是 LLM API key 失效 / 余额 | 在 `https://platform.deepseek.com/` 看 key 状态 |

---

## 10. 参考

- **PRD.md**：原始产品文档（设计源头）
- **CLAUDE.md**：Claude Code 协作约束
- 外部服务：
  - PubChem REST · https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
  - OPSIN · https://www.ebi.ac.uk/opsin/
  - RDKit · https://www.rdkit.org/
  - DeepSeek · https://platform.deepseek.com/
