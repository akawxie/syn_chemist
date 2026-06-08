# P1 — 重试与容错强化 Spec

## 1. 目标

降低三个模块的间歇性失败率（目前约 30–50% 单次失败需重跑），把"外部依赖抖动"和"LLM 偶发非法 JSON"两类常见故障吸收掉，不让它们冒到 UI 层。

**不在范围**：
- 不做请求结果级别的语义重试（如 LLM 答错 → 重新问）
- 不引入熔断 / circuit breaker，过度工程
- 不引入异步任务队列

---

## 2. 设计

两层重试，错误类型决定策略。**重试必须可观测**：每个响应携带 `retry_count` 字段。

### 2.1 外部 HTTP 重试

适用：`PubChemIUPACProvider.to_iupac` / `OpsinWebProvider.to_smiles` / 4 个 LLM provider 的 `judge()`

| 维度 | 策略 |
|---|---|
| 触发 | `httpx.TimeoutException`, `httpx.HTTPError`, status 5xx / 429 |
| 退避 | 指数：1s, 2s, 4s，附 ±25% jitter |
| 上限 | 3 次（含首次） |
| 不重试 | 4xx (≠429)，认证失败立刻报 |

实现：`tenacity` 的 `@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=10), retry=retry_if_exception_type(...))`，包一个 `tenacity_http_retry` 装饰器复用。

### 2.2 LLM JSON 解析重试

适用：所有 LLM provider 返回后，`extract_json()` 解析失败时

- 条件：`extract_json` 返回 `{}` 且 `raw_text` 非空（说明 LLM 应答了但不是合法 JSON）
- 策略：只重试 1 次，追加 system 消息：`Your previous response was not valid JSON. Return ONLY the JSON object, no markdown fences, no prose.`
- 超过：返回 `{"parsed": {}, "raw_text": <last>, "json_retry": true}`，前端的 `NarrativeBlock` 会展示 raw_text 兜底

实现：在 `backend/app/llm/base.py` 加 `try_parse_or_reprompt(provider, system, user) -> JudgeResult`，每个 module 调用此函数而非 provider 直接调用。

### 2.3 可观测性

`JudgeResult` 新增字段：
```python
retry_count: int = 0          # HTTP retry 次数
json_retry: bool = False      # 是否触发过 JSON reprompt
```

前端 `NarrativeBlock` 在 header 旁边显示一个小灰标 `⟳ 2`（重试 2 次），点击展开看原因。

---

## 3. 入口文件

| 文件 | 改动 |
|---|---|
| `backend/app/llm/base.py` | 加 `JudgeResult.retry_count/json_retry` 字段；加 `try_parse_or_reprompt()` |
| `backend/app/llm/_retry.py` (新建) | 共享 `tenacity_http_retry` 装饰器 |
| `backend/app/llm/{deepseek,openai_provider,anthropic_provider,gemini_provider}.py` | `judge()` 加装饰器；捕获异常计数 |
| `backend/app/pipeline/naming.py` | `PubChemIUPACProvider.to_iupac`, `OpsinWebProvider.to_smiles` 加装饰器 |
| `backend/app/modules/{fga,conditions,retro}.py` | 改用 `try_parse_or_reprompt` |
| `frontend/lib/types.ts` | `JudgeMeta` 加 `retry_count`, `json_retry` |
| `frontend/components/NarrativeBlock.tsx` | header 展示重试 chip |

---

## 4. 测试样例

### 4.1 单元测试（必须）

`backend/tests/test_retry.py` —— 全用 mock，无网络。

| 用例 | mock | 期望 |
|---|---|---|
| `test_pubchem_503_then_200` | httpx 第 1 次 503，第 2 次 200 | 返回成功结果，`retry_count == 1` |
| `test_pubchem_all_503` | 连续 3 次 503 | 抛 `RetryError`，被 normalize 链兜底成 "iupac unavailable" |
| `test_pubchem_404_no_retry` | 第 1 次 404 | 立刻返回空 IUPAC，**未触发** retry（计数器 == 0） |
| `test_pubchem_timeout` | `httpx.TimeoutException` 2 次 → 第 3 次成功 | `retry_count == 2` |
| `test_llm_json_reprompt_success` | provider 第 1 次返回 `不是JSON只是说明`，第 2 次返回合法 JSON | `json_retry == True`，`parsed` 非空 |
| `test_llm_json_reprompt_fail` | provider 两次都返回非 JSON | `parsed == {}`，`raw_text == 第二次的文本`，`json_retry == True` |
| `test_llm_401_no_retry` | 第 1 次 401 | 立即抛认证错误，**不重试**（key 错重试是浪费） |

mock 模板（示意）：
```python
def make_httpx_mock(responses):
    """responses: list of (status, body) or Exception"""
    calls = {"n": 0}
    def fake(*a, **kw):
        i = calls["n"]; calls["n"] += 1
        r = responses[i]
        if isinstance(r, Exception): raise r
        return httpx.Response(r[0], text=r[1])
    return fake, calls
```

### 4.2 集成测试（standalone，标记 `@pytest.mark.slow`，CI 跳过）

`backend/tests/integration/test_retry_real.py`

| 用例 | 触发方法 | 期望 |
|---|---|---|
| `test_pubchem_real_aspirin` | 真实调用 PubChem，正确分子 `CC(=O)Oc1ccccc1C(=O)O` | 返回 IUPAC 含 `acetyl`，`retry_count == 0`（happy path） |
| `test_bad_api_key_fails_fast` | 把 `DEEPSEEK_API_KEY` 改成 `sk-invalidxxx` | 应 401 立刻报错；总耗时 < 5s（证明没退避乱重试） |

### 4.3 端到端验证（手动）

在三个 tab 各跑 5 次：
- `CCO`（ethanol）→ FGA
- `CC(=O)O.CCO>>CCOC(=O)C` → Conditions
- `CC(=O)Oc1ccccc1C(=O)O`（aspirin）→ Retro

**通过标准**：5 次全部首次返回结果（无 500、无空白），UI 看到的 `retry_count` 偶尔 ≥1 是正常的（说明系统在容错），但**不应有连续 3 个用例 `retry_count >= 2`**（说明上游真的挂了，与本次改动无关）。

---

## 5. 测试闭环

```
git push
  → GitHub Actions
    → ruff check
    → pytest -m "not slow"  ← 4.1 全跑，应全绿
  → 本地手动
    → pytest -m slow         ← 4.2 真实网络（带 API key）
    → 浏览器跑 4.3            ← 人工 5×3 用例
```

**绿灯条件**：
1. CI 上 unit 全过
2. 本地 slow 测试至少在 3/4 用例通过（PubChem 偶尔抖是允许的）
3. 手动 5×3=15 次 UI 调用，**首次成功率 ≥ 14/15**

---

## 6. 验收标准（PR 合并门槛）

- [ ] `pytest -m "not slow"` 全绿
- [ ] 现有 golden tests 不回归
- [ ] UI 上能肉眼看到 `⟳ N` 重试 chip（人工注一次 PubChem 域名错误验证）
- [ ] 改后跑 `time pytest -m "not slow"` 总耗时增加 < 5s（mock 不该慢）
- [ ] 文档：README 加一段 "How retries work"，3 行内说清

**预估工时**：0.5–1 天
