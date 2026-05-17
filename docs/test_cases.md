# AI_chemist 测试案例集

按模块整理的人工金标（golden set）。每个案例给出输入、正确答案的化学要点、以及评估系统输出是否合格的判断准则。可以直接当 manual QA / regression set 用。

> 约定：所有 SMILES 已通过 RDKit canonical 化；IUPAC 来自 PubChem。

---

## Module A — Functional Groups

评估目标：模型能否识别所有显著基团 + 给出合理的安全/反应性等级。"合格"标准在每条下方列出。

### A1. 乙醇 — 最简单基线

| | 值 |
|---|---|
| 输入 SMILES | `CCO` |
| 期望 IUPAC | `ethanol` |
| Round-trip | OK (1.0) |
| 期望 confidence | ≥ 0.9 |

**正确基团列表**
| 基团 | 严重度 | 化学家理由 |
|---|---|---|
| primary alcohol | low | 醇羟基本身无固有危险，常规试剂可处理 |
| flammable solvent | (隐性 / 非典型 FG) | 闪点 13°C，需注意火源——不强制要求 LLM 提及 |

**判合格的最低条件**
- detected_groups 含 `alcohol`
- LLM alerts 至少给出 alcohol/ethanol，severity=low
- pass_rate = 1.0

---

### A2. 阿司匹林 — 经典多基团

| | 值 |
|---|---|
| 输入 SMILES | `CC(=O)Oc1ccccc1C(=O)O` |
| 期望 IUPAC | `2-acetyloxybenzoic acid` |
| Round-trip | OK (1.0) |

**正确基团列表**
| 基团 | 严重度 | 理由 |
|---|---|---|
| carboxylic acid | low | 弱酸 (pKa ~3.5)，吸湿，可与碱成盐 |
| ester (aryl acetate) | low | 室温稳定；水/碱性条件下易水解 |
| aromatic ring / benzene | low | 苯环本身稳定；不计为 hazard |

**判合格**
- alerts 必须同时识别 `carboxylic_acid` 和 `ester`（不能只报一个）
- 不要报 `phenol`（这个酯化的羟基不应该被识别为游离酚）
- 不该把苯环标为 medium/high

---

### A3. TNT — 多硝基高危分子

| | 值 |
|---|---|
| 输入 SMILES | `Cc1c(cc(cc1[N+](=O)[O-])[N+](=O)[O-])[N+](=O)[O-]` |
| 期望 IUPAC | `2,4,6-trinitrotoluene` |
| Round-trip | OK (1.0) |

**正确基团列表（关键 hazard 案例）**
| 基团 | 严重度 | 理由 |
|---|---|---|
| nitro × 3 | **high** | 多硝基苯类是已知含能炸药；摩擦/冲击/加热敏感 |
| aromatic methyl | low | 不构成额外危险 |

**判合格**
- alerts 必须把 `nitro` 标为 **high** 且 count=3（或显式提到"三硝基/含能/explosive"字样）
- composite confidence 不应 < 0.7
- 这是一个"如果 LLM 没说 high 就是失败"的硬指标

---

### A4. 乙醚 — 自氧化生成过氧化物（chemist trap）

| | 值 |
|---|---|
| 输入 SMILES | `CCOCC` |
| 期望 IUPAC | `1-ethoxyethane`（diethyl ether） |
| Round-trip | OK (1.0) |

**正确基团列表**
| 基团 | 严重度 | 理由 |
|---|---|---|
| dialkyl ether | **medium** | 开瓶长期放置会自氧化生成爆炸性过氧化物，干蒸馏前必须检测；这是经典 chemist trap |
| highly flammable solvent | medium | 闪点 -45°C，蒸气极易燃 |

**判合格**
- LLM alerts 必须提到 **过氧化物风险（peroxide formation）** 或者把 ether 列为 medium
- 如果只把 ether 标 low 而不警告 peroxide → 不合格（说明 LLM 没有做合理的领域判断）

---

### A5. 环氧丙醇（缩水甘油） — 高活性烷化剂

| | 值 |
|---|---|
| 输入 SMILES | `OCC1CO1` |
| 期望 IUPAC | `oxiran-2-ylmethanol`（glycidol） |
| Round-trip | OK (1.0) |

**正确基团列表**
| 基团 | 严重度 | 理由 |
|---|---|---|
| epoxide | **high** | 张力环，强亲电烷化剂；IARC 2A 类致癌物 |
| primary alcohol | low | 普通醇基 |

**判合格**
- `epoxide` 必须 severity=high
- 风险描述应至少提一个：alkylating agent / genotoxic / carcinogen / ring strain
- 不要漏 alcohol

---

### A6. 一个高复杂度真实分子（你之前测的那个）

| | 值 |
|---|---|
| 输入 SMILES | `COc1ccc(OC)c(-n2cccc2CCN)c1` |
| 期望 IUPAC | `2-[1-(2,5-dimethoxyphenyl)pyrrol-2-yl]ethanamine` |
| Round-trip | partial（OPSIN 解析受限） |

**正确基团列表**
| 基团 | 严重度 | 理由 |
|---|---|---|
| methoxy × 2 | low | 芳基甲氧基稳定 |
| pyrrole | low | 芳杂环，碱性弱 |
| aromatic / benzene ring | low | 母核稳定 |
| primary amine | low | 弱碱性、可能为刺激物，无急性危险 |
| **tryptamine-like core** | (隐性) | 与色胺类生物碱结构相似，提示 controlled-substance 类领域知识——加分项不强制 |

**判合格**
- 必须识别 methoxy（用 fragment inventory 已经做到了）
- 必须识别 pyrrole（LLM 用 SMARTS 补充已经做到）
- primary amine 必须出现
- pass_rate ≥ 0.8

---

## Module B — Reaction Conditions

**输入格式**：在顶部输入框写**反应 SMILES**——`reactants > reagents > products`。三段用 `>` 分隔，reagent 段可为空（`A.B>>C`）。多组分用 `.` 串联。前端会自动拆分为三部分并各自渲染结构。

评估目标：给定一对 reactant→product，模型能否：① 正确推断反应类型；② 给出有现实文献依据的条件（溶剂/催化剂/温度/时间/当量）；③ 至少有一条 candidate 接近"教科书答案"。

### B1. 乙醇 → 乙醛（氧化）

| | 值 |
|---|---|
| 反应 SMILES | `CCO>>CC=O` |
| Hint | `oxidation` |

**正确教科书条件**
| 体系 | 溶剂 | 当量 | 温度 / 时间 |
|---|---|---|---|
| **PCC**（吡啶氯铬酸盐） | DCM | 1.5 eq | 室温, 2 h |
| **Swern**（草酰氯 + DMSO + Et3N） | DCM | 1.1 / 2.2 / 4 eq | -78 → -40°C, 1 h |
| **Dess-Martin Periodinane** | DCM | 1.1 eq | 室温, 30 min |
| **TEMPO / 漂白剂** | DCM / H2O | 0.01 / 1.5 eq | 0°C, 1 h |

**判合格**
- reaction_class_guess 含 "oxidation" 或 "alcohol oxidation"
- 至少 1 个 candidate 出现 PCC / Swern / DMP / TEMPO / CrO3 之一
- 不接受 KMnO4 / Jones 作为唯一选择（这些会过氧化到 carboxylic acid，不是 selective 到 aldehyde）

---

### B2. 醋酸 + 乙醇 → 乙酸乙酯（Fischer 酯化）

| | 值 |
|---|---|
| 反应 SMILES | `CC(=O)O.CCO>>CCOC(=O)C` |
| Hint | `esterification` |

**正确教科书条件**
| 体系 | 溶剂 | 催化剂 | 温度 / 时间 |
|---|---|---|---|
| **Fischer 酯化** | 苯/甲苯（Dean-Stark） | conc. H2SO4 (cat.) | 回流, 4–12 h |
| Steglich | DCM | DCC + DMAP | 0°C → 室温, 12 h |
| 酰氯路径（间接） | DCM | SOCl2 → pyridine | 室温 |

**判合格**
- reaction_class_guess 含 "esterification" / "Fischer"
- 至少有 H2SO4 + 加热 + 移水方案，或 DCC/DMAP 路径
- 不接受 NaOH（皂化方向反了）

---

### B3. 苯胺 + 乙酰氯 → 乙酰苯胺（酰化）

| | 值 |
|---|---|
| 反应 SMILES | `Nc1ccccc1.CC(=O)Cl>>CC(=O)Nc1ccccc1` |
| Hint | （留空 → 让 LLM 自己识别） |

**正确教科书条件**
| 体系 | 溶剂 | 当量 | 温度 / 时间 |
|---|---|---|---|
| Acyl chloride amidation | DCM | acetyl chloride 1.1 eq | 0°C → 室温, 1 h |
| 碱（清除 HCl） | (同上) | Et3N 2 eq 或 pyridine 2 eq | — |
| Schotten-Baumann | H2O/DCM 双相 | NaOH 1.5 eq | 0°C, 30 min |

**判合格**
- reaction_class_guess 含 "amide" / "amidation" / "acylation"
- 至少一个 candidate 含碱（Et3N / pyridine / NaOH）
- 不接受没有碱的方案（HCl 会质子化苯胺、抑制反应）

---

### B4. 碘苯 + 苯硼酸 → 联苯（Suzuki 偶联）

| | 值 |
|---|---|
| 反应 SMILES（无 reagent） | `Ic1ccccc1.OB(O)c1ccccc1>>c1ccc(-c2ccccc2)cc1` |
| 反应 SMILES（指定 Pd 为 reagent） | `Ic1ccccc1.OB(O)c1ccccc1>[Pd]>c1ccc(-c2ccccc2)cc1` |
| Hint | `cross-coupling` |

**正确教科书条件**
| 体系 | 溶剂 | 催化剂 | 碱 | 温度 / 时间 |
|---|---|---|---|---|
| Suzuki–Miyaura | 1,4-dioxane / H2O 4:1 | Pd(PPh3)4 5 mol% | K2CO3 2 eq | 80°C, 12 h |
| Suzuki（air-stable） | toluene / EtOH / H2O | Pd(dppf)Cl2 | Cs2CO3 | 80°C |

**判合格**
- reaction_class_guess 必须含 "Suzuki" 或 "cross-coupling"
- candidate 必须含 Pd 催化剂（Pd(PPh3)4 / Pd(OAc)2 / Pd(dppf)Cl2 之一）
- 必须含无机碱（K2CO3 / Cs2CO3 / K3PO4 之一）
- 温度合理（60–100°C）

---

### B5. 苯甲醛 → 苯甲醇（还原）

| | 值 |
|---|---|
| 反应 SMILES | `O=Cc1ccccc1>>OCc1ccccc1` |
| Hint | `reduction` |

**正确教科书条件**
| 体系 | 溶剂 | 当量 | 温度 / 时间 |
|---|---|---|---|
| NaBH4 | MeOH 或 EtOH | 1.0–1.5 eq | 0°C → 室温, 30 min |
| LiAlH4 | 干 Et2O 或 THF | 1.0 eq | 0°C → 室温（更剧烈） |
| H2 / Pd–C | EtOAc | — | 室温, 1 atm |

**判合格**
- reaction_class_guess 含 "reduction"
- candidate 含 NaBH4 / LiAlH4 / H2-Pd 之一
- NaBH4 要标注质子性溶剂（MeOH/EtOH），不要在 THF 里写"无水"——这是细节

---

## Module C — Retrosynthesis

评估目标：模型能否拆解出**化学上合理**的逆合成方向 + 每个中间体 SMILES 合法 + 中间体之间通过已知反应类型衔接。

### C1. 阿司匹林（acetylsalicylic acid）

| | 值 |
|---|---|
| Target | `CC(=O)Oc1ccccc1C(=O)O` |
| 期望 IUPAC | `2-acetyloxybenzoic acid` |

**正确路线**
**Route 1 — 直接乙酰化（教科书唯一路径）**
- Disconnection: O-acyl 键
- Precursors: salicylic acid (`OC(=O)c1ccccc1O`) + acetic anhydride (`CC(=O)OC(C)=O`) 或 acetyl chloride
- Conditions: H2SO4 cat. / 室温 / 30 min

**判合格**
- 必须返回至少 1 条以 salicylic acid 为前体的路线
- 中间体 SMILES 通过 RDKit `is_valid_smiles` 检测
- 不接受拆掉苯环的"野路子"

---

### C2. 对乙酰氨基酚（paracetamol / acetaminophen）

| | 值 |
|---|---|
| Target | `CC(=O)Nc1ccc(O)cc1` |
| 期望 IUPAC | `N-(4-hydroxyphenyl)acetamide` |

**正确路线**
**Route 1 — 由 4-aminophenol 乙酰化（工业路径）**
- Precursors: 4-aminophenol (`Nc1ccc(O)cc1`) + acetic anhydride
- Conditions: H2O / AcOH / 80°C

**Route 2 — 由对硝基苯酚还原 + 乙酰化（教科书 retrosynthesis）**
- Step 1: nitrobenzene → 4-nitrophenol（硝化）
- Step 2: 4-nitrophenol → 4-aminophenol（Sn/HCl 或 H2/Pd-C 还原）
- Step 3: + Ac2O → product

**判合格**
- 至少 1 条路线含 4-aminophenol 中间体
- 加分：含还原硝基的步骤
- 中间体 SMILES 必须全部合法

---

### C3. 布洛芬（ibuprofen）

| | 值 |
|---|---|
| Target | `CC(C)Cc1ccc(C(C)C(=O)O)cc1` |
| 期望 IUPAC | `2-[4-(2-methylpropyl)phenyl]propanoic acid` |

**正确路线**
**Route 1 — Boots 工艺（经典 6 步）**
- isobutylbenzene → Friedel-Crafts 乙酰化 → 4-isobutylacetophenone
- → Darzens 反应 → 缩水甘油酯
- → 水解、脱羧、重排 → 醛
- → HCN 加成 → cyanohydrin
- → 水解 → 2-(4-isobutylphenyl)propanoic acid

**Route 2 — BHC 工艺（绿色 3 步，工业现行）**
- isobutylbenzene → Friedel-Crafts 乙酰化（HF cat.） → 4-isobutylacetophenone
- → H2 / Raney Ni → 1-(4-isobutylphenyl)ethanol
- → CO / Pd-cat. carbonylation → ibuprofen

**判合格**
- 至少 1 条路线以 isobutylbenzene 或 4-isobutylacetophenone 为前体
- 含 Friedel-Crafts 这一步
- 不接受直接"装上 -CH(CH3)COOH"这种非合成可行的拆分

---

### C4. 普鲁卡因（procaine）

| | 值 |
|---|---|
| Target | `CCN(CC)CCOC(=O)c1ccc(N)cc1` |
| 期望 IUPAC | `2-(diethylamino)ethyl 4-aminobenzoate` |

**正确路线**
- **Disconnection 1 (ester)**: 4-aminobenzoic acid (PABA, `Nc1ccc(C(=O)O)cc1`) + 2-(diethylamino)ethanol (`CCN(CC)CCO`)
  - Conditions: H2SO4 cat. or DCC/DMAP
- **Disconnection 2 (amine)**: 4-nitrobenzoate ester + 还原 NO2 → NH2 (Sn/HCl)

**判合格**
- 至少 1 条路线含 PABA + N,N-diethylaminoethanol 为前体
- 加分：含 4-nitrobenzoate 中间体作为更早 step
- 不接受直接合成苯环的方案

---

### C5. 水杨酸甲酯（methyl salicylate / 冬青油）

| | 值 |
|---|---|
| Target | `COC(=O)c1ccccc1O` |
| 期望 IUPAC | `methyl 2-hydroxybenzoate` |

**正确路线**
- **Disconnection**: salicylic acid (`OC(=O)c1ccccc1O`) + methanol
- Conditions: Fischer 酯化 — H2SO4 cat. / 苯回流 with Dean-Stark / 5 h
- 或 Steglich — DCC / DMAP / DCM / 室温

**判合格**
- 路线必须以 salicylic acid 为前体
- 反应类型必须是 esterification

---

## 一次跑完所有案例

把这个脚本保存在 `backend/scripts/run_golden.py`（手动建），喂给 `pytest -m slow` 或直接跑：

```python
import asyncio, httpx, json

BASE = "http://127.0.0.1:8000/api"

FGA = ["CCO", "CC(=O)Oc1ccccc1C(=O)O",
       "Cc1c(cc(cc1[N+](=O)[O-])[N+](=O)[O-])[N+](=O)[O-]",
       "CCOCC", "OCC1CO1", "COc1ccc(OC)c(-n2cccc2CCN)c1"]
CONDITIONS = [("CCO", None, "CC=O", "oxidation"),
              ("CC(=O)O.CCO", None, "CCOC(=O)C", "esterification"),
              ("Nc1ccccc1.CC(=O)Cl", None, "CC(=O)Nc1ccccc1", None),
              ("Ic1ccccc1.OB(O)c1ccccc1", "[Pd]", "c1ccc(-c2ccccc2)cc1", "cross-coupling"),
              ("O=Cc1ccccc1", None, "OCc1ccccc1", "reduction")]
RETRO = ["CC(=O)Oc1ccccc1C(=O)O",
         "CC(=O)Nc1ccc(O)cc1",
         "CC(C)Cc1ccc(C(C)C(=O)O)cc1",
         "CCN(CC)CCOC(=O)c1ccc(N)cc1",
         "COC(=O)c1ccccc1O"]

async def run():
    async with httpx.AsyncClient(timeout=180.0) as c:
        for s in FGA:
            r = await c.post(f"{BASE}/fga", json={"input": s})
            print("FGA", s[:25], "→", r.json().get("confidence", {}).get("composite"))
        for a, rg, b, h in CONDITIONS:
            r = await c.post(f"{BASE}/conditions",
                             json={"reactant": a, "reagent": rg, "product": b,
                                   "reaction_class_hint": h})
            print("COND", a[:20], "→", b[:20], "→", r.json().get("reaction_class_guess"))
        for t in RETRO:
            r = await c.post(f"{BASE}/retro", json={"target": t})
            print("RETRO", t[:25], "routes=", len(r.json().get("routes", [])))

asyncio.run(run())
```

---

## 评分卡（手动 QA 用）

每个案例打 0–3 分：

| 分 | 含义 |
|---|---|
| 3 | 完美——满足"判合格"所有条件 |
| 2 | 主体正确但漏了 1 项次要细节 |
| 1 | 关键点漏或错 |
| 0 | 完全错（如 TNT 没被标 high） |

参考分布：
- Module A：6 案 × 3 = 18 满分，期望 ≥ 14
- Module B：5 案 × 3 = 15 满分，期望 ≥ 11
- Module C：5 案 × 3 = 15 满分，期望 ≥ 10（retrosynthesis 难度更高，分数预期偏低）
