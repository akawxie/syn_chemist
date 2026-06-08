# Secrets & API Key Handling

本项目使用多把外部 API key（DeepSeek、OpenAI、Anthropic、Gemini）。仓库为 **public**，因此对密钥的处理必须严格分层。

## 1. 信任边界

| 边界 | 是否会进 GitHub | 是否会进容器镜像 | 是否会进日志 / 缓存 |
|---|---|---|---|
| Claude Code 对话（聊天上下文） | 否（Claude 不主动 push） | — | — |
| 本地 `.claude/projects/*.jsonl` | **否**（被 root `.gitignore` 排除） | 否 | 是（本地磁盘） |
| `backend/.env` | **否**（被 `.gitignore` 排除） | **否**（被 `.dockerignore` 排除） | 否 |
| `backend/.env.example` | 是（仅作模板，全空值） | 否 | 否 |
| 用户在 UI Settings 填的 key（P4） | — | — | **绝对禁止**进任何持久化 |
| 后端 logger 输出 | — | — | **绝对禁止** |

## 2. 在聊天中粘贴 key 是否会泄露到 GitHub？

**不会自动泄露。** Claude Code 只能通过工具读写本地文件，不会把对话内容外发。聊天里出现 key **不等于** GitHub 上有这把 key。

但有两个**次要**风险，做纵深防御：
1. 本地 `.claude/projects/*.jsonl` 会写聊天历史；如果你将来分享整个项目目录（含隐藏文件）/ 备份到云盘 / 截图给他人，key 会在那个文件里。**`.claude/` 已经在 `.gitignore`**，不会进 GitHub，但本地磁盘风险仍在。
2. 聊天作为 prompt 经过 Anthropic 服务。按 Anthropic 隐私政策不用于训练，但凡留在"非完全自己掌控"的位置，最稳的做法都是定期轮换。

## 3. 核查 key 是否进了 git 历史

仓库已 public，任何 commit 进去过的 secret 都视为永久泄露（即使后续 force-push 删掉，GitHub 自动扫描和镜像站也都拿到了）。

**必须在 push 前跑一遍**这些检查：

```bash
cd /Users/xiewenjun/Documents/coding/AI_chemist

# 1. 检查具体的 key 字面值（替换为你要查的）
git log --all -p -S 'AIzaSyCkQtUQB6Hkm7O3DwjpvZvkd6a0t1vzIuo' 2>/dev/null
git log --all -p -S 'sk-5f86bf846fca4337babf6d2c5025d9e9' 2>/dev/null

# 2. 检查常见 key 前缀
git log --all -p -S 'sk-' 2>/dev/null | head -50          # OpenAI/DeepSeek/Anthropic 风格
git log --all -p -S 'AIza' 2>/dev/null | head -50         # Google 风格
git log --all -p -S 'sk-ant-' 2>/dev/null | head -50      # Anthropic
git log --all -p -S 'ghp_' 2>/dev/null | head -50         # GitHub PAT

# 3. 检查 .env 是否曾经被 tracked
git log --all --full-history -- backend/.env
git log --all --full-history -- .env

# 4. 检查工作树当前未被 ignore 的潜在密钥文件
git ls-files | grep -E '(\.env$|\.env\.|secrets|credentials)'
```

**通过标准**：以上 7 条命令**全部输出为空**。

任意一条有命中 → 立刻：
1. 在对应平台 revoke 该 key
2. 生成新 key 写进 `backend/.env`
3. 考虑用 `git filter-repo` 清理历史（但要假设原 key 已泄露）

## 4. .gitignore 必须包含

仓库根 `.gitignore`（已就位，定期 audit）：

```
# secrets
.env
.env.local
.env.*.local
*.pem
*.key
secrets/

# claude local state
.claude/settings.local.json
.claude/projects/

# python
.venv/
__pycache__/
*.pyc
*.db
*.sqlite*

# node / next
node_modules/
.next/
.vercel/

# os
.DS_Store
```

## 5. 提交前 pre-commit hook（推荐 P1 阶段顺手加）

`.pre-commit-config.yaml`：

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
```

或更轻量：在 `.git/hooks/pre-commit` 写一个 grep：

```bash
#!/bin/sh
if git diff --cached | grep -E '(sk-[a-zA-Z0-9]{20,}|AIza[A-Za-z0-9_-]{30,}|sk-ant-[A-Za-z0-9-]{20,})'; then
  echo "ERROR: potential API key in staged changes"
  exit 1
fi
```

## 6. P4 上线后的运行时规则

详见 [P4-deployment.md §3.2 / §5.4](./P4-deployment.md)，核心规则复述：

- **永不** `logger.*(key)` —— code review 时 grep
- **永不**把 key 放进 query string
- **永不**把 key 回显进 response body
- **永不**把 key 进 cache key（SQLite 持久化）
- **永不**通过 GET 传 key
- 后端调用结束后局部变量立刻 `del`，不入任何全局结构
- HTTPS 强制，CORS 限定 origin

## 7. 用户在聊天里贴的 key 该不该 revoke

判断流程：

1. 跑 §3 的 7 条命令，**全空** → 这把 key 没进过 git，public 仓库本身不构成泄露风险
2. 评估其他暴露面：是否截图发过 / 备份过 `.claude/` / 通过其他渠道发过
3. 风险可接受 → 保留使用，写进 `backend/.env`
4. 风险不可接受 → 平台 revoke + 生成新 key

> **决策建议**：操作成本很低（Google AI Studio / DeepSeek 后台 revoke + 生成新 key 通常 < 1 分钟），如果有疑虑就轮换，没有损失。
