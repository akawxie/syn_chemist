# Specs

按 [roadmap](../roadmap.md) 的优先级展开的实现 spec。每份含：目标、设计、入口文件、测试样例、测试闭环、验收标准。

| Spec | 主题 | 工时 |
|---|---|---|
| [P1 — Retry](./P1-retry.md) | 三个模块加重试与 LLM JSON reprompt | 0.5–1 天 |
| [P2 — Image Input](./P2-image-input.md) | 图片输入 + Gemini 2.5 Flash Lite 视觉 OCR | 1.5–2 天 |
| [P3 — i18n](./P3-i18n.md) | UI 中英文切换 + LLM 输出双语 | 1–1.5 天 |
| [P4 — Deployment](./P4-deployment.md) | 公网部署 + 用户自带 API key | 2–3 天 |
| [Security & Secrets](./security-secrets.md) | 密钥处理规范 + 仓库 audit 命令 | 横切 |

## 通用约定

- 所有改动**必须有 unit 测试**，CI 上 `pytest -m "not slow"` 全绿才能合并
- 涉及真实外部依赖（LLM、PubChem、OPSIN、Gemini）的测试标 `@pytest.mark.slow`，本地手动跑
- 任何引入 API key 流转的改动，必须先读 [security-secrets.md](./security-secrets.md) 第 §3 §6 节
- 写 PR 前跑 [security-secrets.md §3](./security-secrets.md#3-核查-key-是否进了-git-历史) 的 7 条 audit 命令，全部输出为空才 push

## 实施顺序建议

P1 → P2 → P3 → P4。理由：
- P1 不引入新依赖，降低后续 P2/P3/P4 调试时的噪音
- P2 新增 Gemini vision 路径，独立可测
- P3 改动面广但浅，最好在 P2 完成后做（避免 ImageInput 组件还要再翻译一遍）
- P4 部署放最后，前面三个稳定之后再上线
