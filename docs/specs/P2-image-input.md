# P2 — 图片输入 + Gemini Flash 视觉解析 Spec

## 1. 目标

让用户上传分子结构图（ChemDraw 截图、文献图、手画拍照）作为输入，后端用 Gemini Flash 的视觉模型 OCR 出 SMILES，再走原有 normalize 链做闭环验证。

**关键设计原则**（继承 PRD）：**LLM 视觉 = 判读器，不是真相源**。Gemini 返回 SMILES 后必须走 PubChem/OPSIN round-trip；round-trip 失败时 UI 显式提示 "OCR result not verified"，不静默通过。

**视觉模型选型**：使用 **`gemini-2.5-flash-lite`** 作为默认（按 Google 官方最新可用模型；用户最初提及的 "Gemini 3.1 Flash Lite" 在写本文时不存在，由 `GEMINI_VISION_MODEL` 环境变量可覆盖）。

---

## 2. 设计

```
┌─────────────────────────┐
│  Frontend ImageInput    │ 拖拽 / 点击 / 粘贴（Ctrl+V）
│  - 限 5MB / png|jpg|webp│
│  - 本地预览缩略图        │
└──────────┬──────────────┘
           │ multipart/form-data
           ▼
┌─────────────────────────┐
│  POST /api/molecule/    │
│       from_image        │ ← 复用现有 API 路径前缀
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  GeminiVisionOCR        │ base64 → Gemini 2.5 Flash Lite
│  prompt 强约束 SMILES   │ 返回 raw_smiles
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  RoundTripValidator     │ 现有 normalize 链
│  PubChem + OPSIN        │ → NormalizedMolecule
└──────────┬──────────────┘
           │
           ▼
   {smiles, iupac, round_trip_ok, ocr_raw, warning?}
```

### 2.1 OCR 提示词（写进代码，不暴露给用户）

```
You are a chemical-structure OCR engine.
Look at the image and return ONLY the canonical SMILES for the depicted molecule.
Rules:
- Return ONLY SMILES, no markdown, no explanation, no quotes.
- If multiple disconnected molecules appear, join with "."
- If the image clearly is NOT a chemical structure (photo, text-only, blank), return the single word: NOT_A_MOLECULE
- If you can see a structure but cannot determine atoms/bonds confidently, return: UNCERTAIN
```

后端代码侧三种返回值处理：
- 合法 SMILES → 进 round-trip
- `NOT_A_MOLECULE` → API 返回 422 + 友好提示
- `UNCERTAIN` 或解析失败 → 200 但带 `warning: "OCR could not confidently identify the structure"`，前端给醒目提示但不阻断

### 2.2 文件约束

| 项 | 限制 | 何处校验 |
|---|---|---|
| 文件大小 | ≤ 5 MB | 前端预校验 + 后端 `Content-Length` 二次校验 |
| MIME | `image/png`, `image/jpeg`, `image/webp` | 后端用 `python-magic` 或 PIL `Image.open` 探测，**不信任** `Content-Type` header |
| 分辨率 | 短边 ≥ 200 px，长边 ≤ 4096 px | 后端用 PIL 校验；过小报错，过大缩放到 2048 |
| 一次上传 | 1 张 | API 接 `UploadFile`，不接 list |

### 2.3 密钥处理

- **后端默认使用环境变量** `GEMINI_API_KEY`（写在 `backend/.env`，仓库不带）
- 为 P4 公网部署预留：如果请求带 header `X-User-LLM-API-Key` 且 `X-User-LLM-Provider: gemini`，**优先使用 header**（P4 完整实现，P2 阶段只留 hook 不强求）

---

## 3. 入口文件

| 文件 | 改动 |
|---|---|
| `backend/app/llm/gemini_vision.py` (新建) | `GeminiVisionOCR.smiles_from_image(image_bytes) -> OCRResult` |
| `backend/app/api/molecule_image.py` (新建) | `POST /api/molecule/from_image`，`UploadFile` |
| `backend/app/api/__init__.py` | 注册新路由 |
| `backend/app/config.py` | 加 `gemini_api_key`, `gemini_vision_model` (默认 `"gemini-2.5-flash-lite"`) |
| `backend/pyproject.toml` | 已有 `google-generativeai`；补 `Pillow`, `python-magic` |
| `backend/.env.example` | 加 `GEMINI_API_KEY=`, `GEMINI_VISION_MODEL=gemini-2.5-flash-lite` |
| `frontend/components/ImageInput.tsx` (新建) | 拖拽 / 粘贴 / 选择，缩略图，上传按钮 |
| `frontend/components/MoleculeInput.tsx` | 在输入框旁加 📷 切换按钮，切到图片模式时挂载 ImageInput |
| `frontend/lib/api.ts` | 加 `postMoleculeImage(file: File)` |
| `frontend/lib/types.ts` | 加 `OCRResult` 类型 |

---

## 4. 测试样例

### 4.1 单元测试（mock Gemini，无网络）

`backend/tests/test_gemini_vision_ocr.py`

| 用例 | mock Gemini 返回 | 期望 |
|---|---|---|
| `test_ocr_clean_smiles` | `"CCO"` | `OCRResult(smiles="CCO", confidence_signal="ok")` |
| `test_ocr_smiles_with_fences` | `"```smiles\nCCO\n```"` | 自动剥离 → `"CCO"` |
| `test_ocr_not_molecule` | `"NOT_A_MOLECULE"` | 抛 `NotAMoleculeError`，被 API 转 422 |
| `test_ocr_uncertain` | `"UNCERTAIN"` | `OCRResult(smiles="", warning="OCR uncertain")` |
| `test_ocr_garbage` | `"I see a molecule with..."` | `OCRResult(smiles="", warning="OCR did not return valid SMILES")` |
| `test_ocr_invalid_smiles` | `"XXX@@@"` | RDKit 解析失败 → `warning="OCR returned invalid SMILES: XXX@@@"` |

### 4.2 端点测试（FastAPI TestClient + mock OCR）

`backend/tests/test_api_molecule_image.py`

| 用例 | 输入 | 期望 |
|---|---|---|
| `test_upload_png_ok` | 真实 PNG 4KB + mock OCR 返回 `CCO` | 200, `smiles="CCO"`, `round_trip_ok=True` |
| `test_upload_oversize` | 6 MB 文件 | 413 Payload Too Large |
| `test_upload_pdf_rejected` | 上传 PDF（假冒 image/png header） | 415 Unsupported Media Type（按文件魔数判定） |
| `test_upload_too_small` | 50×50 png | 400, "image too small (min 200px)" |
| `test_upload_round_trip_fails` | mock OCR 返回 `CC` 但 PubChem 返不出 IUPAC | 200, `round_trip_ok=False`, `warning="OCR result not verified"` |
| `test_upload_no_file` | 空 body | 422 (FastAPI 自带) |

### 4.3 集成测试（真实 Gemini，`@pytest.mark.slow`，CI 跳过）

`backend/tests/integration/test_gemini_real.py`

测试用图放在 `backend/tests/fixtures/images/`：

| 图片 | 来源 | 期望 SMILES（标准）| 通过门槛 |
|---|---|---|---|
| `aspirin_pubchem.png` | PubChem 标准结构图 | `CC(=O)Oc1ccccc1C(=O)O` | RDKit `MolToSmiles` 与标准相同 |
| `ibuprofen_chemdraw.png` | ChemDraw 截图 | `CC(C)Cc1ccc(C(C)C(=O)O)cc1` | canonical SMILES 匹配 |
| `ethanol_handdrawn.jpg` | 手画拍照 | `CCO` | 字符串匹配 |
| `caffeine_wikipedia.png` | Wikipedia | `Cn1cnc2c1c(=O)n(C)c(=O)n2C` | canonical SMILES 匹配 |
| `not_molecule_cat.jpg` | 猫照片 | — | 应返回 `NOT_A_MOLECULE` |
| `blank_white.png` | 纯白图 | — | 应返回 `NOT_A_MOLECULE` 或 `UNCERTAIN` |
| `tylenol_blurry.jpg` | 模糊低质 | `CC(=O)Nc1ccc(O)cc1` | 允许 round-trip fail，但**不允许**返回错误结构当成功 |

**通过门槛**：标准清晰图（aspirin/ibuprofen/caffeine/ethanol）≥ 3/4 准确；模糊/拒绝类正确分类（不强求 OCR 准）。

### 4.4 前端测试

`frontend/tests/e2e/image_input.spec.ts` (Playwright)

| 用例 | 操作 | 期望 |
|---|---|---|
| `test_upload_via_button` | 点 📷 → 选 `fixtures/aspirin.png` → 点 Analyze | 看到 SMILES 出现在输入框、FGA 结果展示 |
| `test_upload_via_drag` | 拖拽图片到输入区 | 同上 |
| `test_upload_via_paste` | 焦点在 ImageInput → `Ctrl+V` 粘贴剪贴板图片 | 同上 |
| `test_oversize_blocked` | 选 6MB 图 | 前端直接报错，不发请求 |
| `test_not_molecule_warning` | 上传猫照片 | UI 显示红色 banner: "Not a molecule" |

---

## 5. 测试闭环

```
PR commit
  → GitHub Actions
    → pytest -m "not slow"   ← 4.1 + 4.2 全跑（mock Gemini）
    → frontend typecheck
    → frontend Playwright（4.4，仅本地或预发，CI 跳）
  → 本地手动（PR review 前作者执行）
    → pytest -m slow         ← 4.3 真实调用 Gemini，消耗少量 quota
    → 手动 UI 测：5 张真实图各传一次，肉眼核对结构
```

**绿灯条件**：
1. CI 上 unit + endpoint 全绿
2. 本地 slow 测试 ≥ 4/7 用例通过（视觉 OCR 本身不稳定，这是合理基线）
3. 拒绝类用例（猫照片/空白）**必须 100%** 拒绝——错误地把非分子识别为分子是**最严重的**，会让用户后续分析全错

---

## 6. 验收标准（PR 合并门槛）

- [ ] `pytest -m "not slow"` 全绿
- [ ] UI 三种上传方式（按钮、拖拽、粘贴）都能跑通
- [ ] 5 张 fixture 真实图至少 3 张 OCR + round-trip 全通过
- [ ] 非分子图必定被拒（手测 ≥ 3 张反例）
- [ ] OCR 失败 / round-trip 失败时 UI 有醒目警告，**不允许静默**当成成功
- [ ] `backend/.env.example` 加了 `GEMINI_API_KEY=`，README 加了一段"How image input works"
- [ ] **`backend/.env` 未进 git**（见 `docs/specs/security-secrets.md` 的核查命令）
- [ ] OCR 路径**不写日志**包含 API key（grep `logger.*api_key` 应为空）

**预估工时**：1.5–2 天（主要在 prompt 调参 + 前端三种上传方式 + 真实图回归）
