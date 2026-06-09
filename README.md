# AI_chemist

An AI-assisted workflow for synthetic chemists — functional group alerts, reaction condition recommendations, and retrosynthesis route proposals, each with a verified confidence score.

## What makes it different?

Most AI chemistry tools either trust the model blindly or rely solely on rule-based lookups. **AI_chemist does neither.** It uses a **generate → judge → verify** pipeline:

1. **LLM judges and ranks** — General-purpose models (DeepSeek / GPT / Claude / Gemini) evaluate what's plausible, but are never the source of truth.
2. **Chemistry tools verify** — RDKit, PubChem, and OPSIN independently check every claim: structural legality, atom conservation, functional group matches, SMILES↔IUPAC round-trips.
3. **Confidence is quantified** — Every result carries a composite score (0–100%) built from three independent signals: naming round-trip success, LLM self-assessed certainty, and RDKit verification pass rate.

This means you get **AI insight with chemical accountability** — high-confidence results you can trust, and low-confidence ones clearly flagged for manual review.

## Capabilities

### 🔬 Functional Group Alert

Identify and assess every functional group in your molecule:

- **25 curated hazard SMARTS** detect nitro, azide, peroxide-forming ethers, epoxides, and more — each tagged with severity (low / medium / high).
- **85 RDKit fragment scans** (`fr_*` module) provide a broad substructure inventory.
- **LLM extends coverage** — the model can flag groups the rule library misses (e.g. specific heterocycles, stereochemistry-sensitive motifs) by supplying SMARTS patterns that RDKit then verifies.
- Example: diethyl ether is correctly flagged as **medium** risk with a peroxide-formation warning — not just "ether, low".

### ⚗️ Reaction Condition Recommendation

Given reactants and products, get ranked condition sets:

- The LLM proposes 3–5 plausible candidate conditions (solvent, catalyst, temperature, time, equivalents) citing mainstream literature heuristics.
- RDKit validates reactant/condition compatibility and checks heavy-atom conservation.
- Optional **reaction class hint** (e.g. "Suzuki", "oxidation") constrains the search.
- Supports multi-component reactions and user-specified reagents.

### 🧬 Retrosynthesis Route Proposal

Work backwards from a target molecule to commercially available precursors:

- The LLM proposes 2–4 macro retrosynthetic routes (3–6 steps each) using textbook disconnections.
- Each step includes the reaction class, intermediate SMILES, and a one-line rationale.
- RDKit gates every intermediate for chemical feasibility — invented or impossible structures are caught.
- Intermediate molecules are rendered as structure diagrams inline.

### 🌐 Multilingual Output

Switch between English and Chinese with one click — both the UI and the LLM output language change instantly. Chemistry identifiers (SMILES, IUPAC, reaction names) are never translated; only natural-language fields (rationale, risk, summary) are.

### 📷 Image Input

Upload or paste a structure image — Gemini Flash recognizes the molecule, extracts SMILES, and feeds it into the normal pipeline.

## How it works

```
Your input ──▶ Naming round-trip ──▶ LLM judgment ──▶ RDKit verification ──▶ Scored result
              (SMILES↔IUPAC          (rank & filter)    (structural check)     (confidence %)
               closed-loop check)
```

**Three inviolable design rules:**

1. **LLM = judge + filter, never the source of truth.** Every LLM claim is reverse-verified by chemistry tools.
2. **If it can be round-trip checked, it is.** SMILES → IUPAC → SMILES closure is the canonical example — a mismatch triggers a fallback and lowers confidence.
3. **Confidence is a first-class output**, not optional. It's a weighted composite of round-trip score (30%), LLM self-confidence (30%), and RDKit pass rate (40%).

## Quick Start

### Prerequisites

- Python 3.11
- Node.js 18+
- An LLM API key — [get a DeepSeek key here](https://platform.deepseek.com/api_keys) (default, cheapest option)

### Install

```bash
# Backend
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -e .

# Frontend
cd ../frontend
npm install
```

### Configure

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in your API key:

```ini
DEEPSEEK_API_KEY=sk-your-key-here
```

### Run

Open two terminal windows:

```bash
# Terminal 1 — backend (must use --reload for hot code reload)
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

```bash
# Terminal 2 — frontend
cd frontend
npm run dev
```

Open **http://localhost:3000** and you're ready.

## Usage

### Input formats

The top input box accepts three formats:

| Format | Example | Use for |
|---|---|---|
| SMILES | `CCO` | Single molecule (all three modules) |
| InChI | `InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3` | Single molecule |
| Reaction SMILES | `CC(=O)O.CCO>>CCOC(=O)C` | Reaction Conditions module |

Reaction SMILES uses `>` as separator: `reactants > reagents > products`. The reagent slot can be empty (`A>>C`). Join multiple components with `.` (e.g. `A.B>>C`).

Click the 📷 button to upload a structure image instead — Gemini will auto-detect the molecule.

### Interpreting results

Every result block shows a **confidence badge** (click to expand):

| Score | Meaning |
|---|---|
| 🟢 ≥ 75% | High confidence — results are reliable |
| 🟡 50–75% | Medium — manual review recommended |
| 🔴 < 50% | Low — use with caution |

The composite score is a weighted average of three independent signals:

| Signal | What it measures | Weight |
|---|---|---|
| Round-trip | Did SMILES → IUPAC → SMILES close cleanly? | 30% |
| Judge | How certain is the LLM about its own output? | 30% |
| Verify | What fraction of claims passed RDKit checks? | 40% |

### Switching LLM provider

Edit `backend/.env` — no code changes needed. The server auto-reloads if started with `--reload`.

```ini
# OpenAI
JUDGE_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Anthropic Claude
JUDGE_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
JUDGE_PROVIDER=gemini
GOOGLE_API_KEY=...
```

### Language toggle

Click **EN / 中** in the top-right corner. The UI switches language immediately; the next LLM call will output in the selected language. Chemistry identifiers stay in standard notation.

## macOS note

If you see `Operation not permitted` when accessing project files, go to **System Settings → Privacy & Security → Full Disk Access**, add your Terminal app, then fully quit and reopen Terminal.

## License

MIT
