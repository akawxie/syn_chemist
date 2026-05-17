# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

This repo is **pre-implementation**: only `PRD.md` exists. There is no source code, build system, package manifest, or tests yet. Before writing code, confirm with the user which stack to scaffold (the PRD does not prescribe one). Once scaffolded, replace this section with real build/test/run commands.

## Product (from PRD.md)

**AI_chemist** is an AI-assisted workflow tool for synthetic chemists. Its differentiator is *not* using a chemistry-domain-trained model — it uses general-purpose LLMs (GPT / Claude / Gemini) as **judges and direction filters**, and delegates hard chemistry truth to open-source cheminformatics tools.

The design thesis (important — drives the whole architecture): general LLMs are ~80% accurate at *evaluating whether a proposed plan is reasonable*, but poor at *generating plans from scratch*. So the pipeline is **generate → judge → verify**, with the LLM doing judging/ranking and tools (RDKit, STOUT, OPSIN) doing the factual verification.

## Core pipeline (must be preserved across modules)

User molecule input flows through a fixed multi-stage pipeline. Any new feature should plug into this pipeline rather than bypass it:

1. **Structured input** — user submits SMILES or InChI.
2. **Naming with closed-loop validation** — convert SMILES → IUPAC with **STOUT** (or successor), then convert IUPAC → structure with **OPSIN** and compare back to the original SMILES. Mismatch ⇒ trigger fallback / warning. The naming-tool layer must be **swappable behind an interface** so better tools can be substituted later (the PRD calls this out as a continuous-optimization requirement).
3. **Prompt engineering + LLM inference** — feed the verified IUPAC name + structural features into a **modular prompt template** to get the LLM's directional judgment.
4. **Chemistry verification layer** — re-validate the LLM output with **RDKit**: structural legality, atom conservation, functional-group compatibility, physicochemical plausibility per step.
5. **Structured output** — tables / flow diagrams / step-by-step text, each item carrying a **confidence score** that combines (a) naming round-trip success, (b) LLM self-reported confidence, (c) RDKit verification pass-rate. Items that fail verification are flagged "low confidence" or filtered.

## Functional modules

Three independent but composable modules, each with its own prompt template and verification logic. They share the pipeline above:

- **Module A — Functional Group Alert**: RDKit extracts substructures/topology → LLM judges hazard / instability / steric concerns from name + structure → highlight risky groups.
- **Module B — Reaction Condition Recommendation**: hypothesis-and-test pattern. Pull candidate conditions from open reaction databases → LLM ranks plausibility → RDKit checks reactant/condition compatibility → output ranked conditions (solvent, catalyst, temp, time, equivalents) with scores.
- **Module C — Synthesis Route Recommendation**: LLM proposes macro retrosynthesis directions (disconnections / reaction-type matches) → RDKit gates each intermediate for chemical feasibility → return multiple candidate routes with intermediates and confidence.

## Design rules to enforce in code

- **LLM = judge + filter, never the source of truth.** Don't write features that trust LLM output without a verification step.
- **Every conversion is bidirectionally checked** where possible (SMILES↔IUPAC round-trip is the canonical example).
- **Confidence is a first-class output field**, not optional. Do not return results to the UI without a score derived from the three sources above.
- **The naming/conversion tool layer is pluggable** — design it as a strategy interface from day one so STOUT/OPSIN can be swapped without touching modules A/B/C.

## UI expectations

Minimal: input box, three module tabs, and a molecule-structure rendering area. Each result block shows {summary, reasoning trace, confidence score}.

## External tools referenced by the PRD

- **STOUT** — SMILES → IUPAC (transformer-based, PyPI/GitHub).
- **OPSIN** — IUPAC → structure (EBI).
- **RDKit** — structural and reaction-feasibility validation.
- General LLM APIs (GPT / Claude / Gemini) for the judging step.
