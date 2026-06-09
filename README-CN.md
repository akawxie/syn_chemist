# AI_chemist

AI 辅助的合成化学工作流工具。输入一个分子，获得官能团风险分析、反应条件推荐、逆合成路线建议——每条结果都附带置信度评分。

## 它是怎么工作的？

```
你的输入 → 分子命名验证 → LLM 评判 → 化学工具验算 → 带置信度的结果
```

核心思路：**不盲信 AI，也不只靠规则库**。通用大模型（DeepSeek / GPT / Claude / Gemini）擅长"判断一个方案是否合理"，但不擅长"从零生成正确方案"。所以我们让 LLM 做**评判和筛选**，让专业化学软件（RDKit / PubChem / OPSIN）做**事实验证**，两者交叉打分，给出综合置信度。

三个独立模块，共用同一条验证管线：

| 模块 | 做什么 |
|---|---|
| **官能团警报** | 检测分子中的危险基团，评估热稳定性、冲击敏感性、毒性等实操风险 |
| **反应条件推荐** | 给定反应物和产物，推荐溶剂、催化剂、温度、时间等条件，按可行性排序 |
| **逆合成路线** | 从目标分子反向拆解，给出多条合成路线及中间体 |

## 快速开始

### 前置要求

- Python 3.11
- Node.js 18+
- 一个 LLM API Key（默认用 DeepSeek，[在这里申请](https://platform.deepseek.com/api_keys)）

### 安装

```bash
# 后端
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -e .

# 前端
cd ../frontend
npm install
```

### 配置

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入你的 API Key：

```ini
DEEPSEEK_API_KEY=sk-你的密钥
```

### 启动

开两个终端窗口：

```bash
# 终端 1 — 后端（必须加 --reload）
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

```bash
# 终端 2 — 前端
cd frontend
npm run dev
```

打开 **http://localhost:3000** 即可使用。

## 使用方法

### 输入格式

顶部输入框支持三种格式：

| 格式 | 示例 | 用途 |
|---|---|---|
| SMILES | `CCO` | 单个分子 |
| InChI | `InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3` | 单个分子 |
| 反应 SMILES | `CC(=O)O.CCO>>CCOC(=O)C` | 反应条件推荐 |

反应 SMILES 用 `>` 分隔三段：`反应物 > 试剂 > 产物`。试剂段可为空（`A>>C`）。多组分用 `.` 连接。

也可以点 📷 按钮上传分子结构图片，系统会用 Gemini 自动识别。

### 语言切换

右上角 **EN / 中** 按钮可切换界面语言和 LLM 输出语言。化学标识符（SMILES、IUPAC 名称、反应类型）不会被翻译，只翻译自然语言描述。

### 结果解读

每条结果右上角有**置信度徽章**，点击可展开三个分量：

| 分量 | 含义 | 权重 |
|---|---|---|
| round-trip | SMILES → IUPAC → SMILES 闭环是否成功 | 30% |
| judge | LLM 自评的确定程度 | 30% |
| verify | RDKit 验证通过率 | 40% |

- 🟢 **≥ 75%** — 高置信度，结果可靠
- 🟡 **50–75%** — 中等，建议人工复核
- 🔴 **< 50%** — 低置信度，谨慎参考

### 切换 LLM

编辑 `backend/.env` 即可切换，无需改代码：

```ini
# 用 OpenAI
JUDGE_PROVIDER=openai
OPENAI_API_KEY=sk-...

# 用 Claude
JUDGE_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# 用 Gemini
JUDGE_PROVIDER=gemini
GOOGLE_API_KEY=...
```

切换后 uvicorn 会自动重载（如果用了 `--reload`）。

## macOS 用户注意

如果终端报 `Operation not permitted`，去 **系统设置 → 隐私与安全性 → 完全磁盘访问权限**，添加你的终端应用，然后完全退出并重新打开终端。

## 许可证

MIT
