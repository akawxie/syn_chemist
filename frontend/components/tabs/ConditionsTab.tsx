"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { ConditionsResponse, VisionConditionsResponse } from "@/lib/types";
import { useLang } from "@/components/LanguageContext";
import { t } from "@/lib/i18n";
import type { NormBundle } from "../MoleculeInput";
import { NarrativeBlock } from "../NarrativeBlock";
import { ResultBlock } from "../ResultBlock";
import { VisionPanel, ConfidenceChip } from "../VisionPanel";

export function ConditionsTab({ bundle }: { bundle: NormBundle }) {
  const [hint, setHint] = useState("");
  const [data, setData] = useState<ConditionsResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [visionData, setVisionData] = useState<VisionConditionsResponse | null>(null);
  const { lang } = useLang();

  const inputErr = validate(bundle);

  async function run() {
    if (inputErr) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await api.conditions(
        bundle.reactant!.canonical_smiles,
        bundle.product!.canonical_smiles,
        {
          reagent: bundle.reagent?.canonical_smiles ?? null,
          reaction_class_hint: hint.trim() || null,
          lang,
        },
      );
      setData(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded border border-border bg-panel p-3 text-xs">
        <div className="mb-1 font-semibold text-gray-300">Reaction input format</div>
        <div className="text-gray-400">
          In the top box, write reaction SMILES:{" "}
          <code className="font-mono text-accent">reactants &gt; reagents &gt; products</code>.
          The reagent slot can be empty.
        </div>
        <ul className="mt-2 space-y-0.5 text-gray-400">
          <li>
            <code className="font-mono text-gray-300">CCO&gt;&gt;CC=O</code> — ethanol oxidation
          </li>
          <li>
            <code className="font-mono text-gray-300">CC(=O)O.CCO&gt;&gt;CCOC(=O)C</code> — Fischer
            esterification (multi-component reactant)
          </li>
          <li>
            <code className="font-mono text-gray-300">Ic1ccccc1.OB(O)c1ccccc1&gt;[Pd]&gt;c1ccc(-c2ccccc2)cc1</code>{" "}
            — Suzuki, with Pd reagent specified
          </li>
        </ul>
      </div>

      {inputErr && (
        <div className="rounded border border-amber-700 bg-amber-900/20 p-3 text-sm text-amber-200">
          {inputErr}
        </div>
      )}

      <div>
        <label className="mb-1 block text-xs uppercase tracking-wide text-gray-400">
          Reaction class hint (optional)
        </label>
        <input
          value={hint}
          onChange={(e) => setHint(e.target.value)}
          placeholder="e.g. oxidation, Suzuki, SN2 (leave blank to let the LLM guess)"
          className="w-full rounded border border-border bg-panel px-3 py-2 text-sm text-gray-100 outline-none focus:border-accent"
        />
      </div>

      <button
        onClick={run}
        disabled={busy || !!inputErr}
        data-testid="run-conditions"
        className="rounded bg-accent px-4 py-2 text-sm font-semibold text-bg disabled:opacity-50"
      >
        {busy ? t(lang, "btn.analyzing") : t(lang, "btn.analyze_conditions")}
      </button>

      {err && (
        <div className="rounded border border-rose-700 bg-rose-900/30 p-3 text-sm text-rose-200">
          {err}
        </div>
      )}

      {data && !data.error && (
        <ResultBlock
          title={`${t(lang, "result.title.conditions")}${data.reaction_class_guess ? ` · ${data.reaction_class_guess}` : ""}`}
          confidence={data.confidence}
          verification={data.verification}
          judge={data.judge}
          outputLanguage={data.output_language}
        >
          {data.candidates.length === 0 ? (
            <div className="text-xs text-gray-500">{t(lang, "result.no_results")}</div>
          ) : (
            <div className="overflow-x-auto" data-testid="cond-table">
              <table className="w-full text-xs">
                <thead className="text-left text-gray-500">
                  <tr>
                    <th className="py-1 pr-3">#</th>
                    <th className="py-1 pr-3">Solvent</th>
                    <th className="py-1 pr-3">Catalyst</th>
                    <th className="py-1 pr-3">Base / Additive</th>
                    <th className="py-1 pr-3">Temp</th>
                    <th className="py-1 pr-3">Time</th>
                    <th className="py-1 pr-3">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {data.candidates.map((c, i) => (
                    <tr key={i} className="border-t border-border align-top">
                      <td className="py-2 pr-3 text-gray-500">{i + 1}</td>
                      <td className="py-2 pr-3">{c.solvent ?? "—"}</td>
                      <td className="py-2 pr-3">{c.catalyst ?? "—"}</td>
                      <td className="py-2 pr-3">{(c as { base_or_additive?: string }).base_or_additive ?? "—"}</td>
                      <td className="py-2 pr-3">{c.temperature ?? "—"}</td>
                      <td className="py-2 pr-3">{c.time ?? "—"}</td>
                      <td className="py-2 pr-3 font-mono">
                        {typeof c.score === "number"
                          ? c.score.toFixed(2)
                          : typeof (c as { self_confidence?: number }).self_confidence === "number"
                          ? (c as { self_confidence: number }).self_confidence.toFixed(2)
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-2 space-y-1 text-xs text-gray-400">
                {data.candidates.map((c, i) =>
                  c.rationale ? (
                    <div key={i}>
                      <span className="text-gray-500">#{i + 1}:</span> {c.rationale}
                    </div>
                  ) : null,
                )}
              </div>
            </div>
          )}

          <NarrativeBlock
            narrative={data.narrative}
            thin={
              data.candidates.length === 0 ||
              data.candidates.every(
                (c) => !c.solvent && !c.catalyst && !c.temperature && !c.time,
              )
            }
          />
        </ResultBlock>
      )}

      {data?.error && (
        <div className="rounded border border-amber-700 bg-amber-900/30 p-3 text-sm text-amber-200">
          {data.error}
        </div>
      )}

      {/* ── Vision direct analysis ── */}
      <div className="mt-2 border-t border-border pt-4">
        <div className="mb-2 text-xs uppercase tracking-wide text-gray-500">
          Direct Image Analysis <span className="normal-case text-gray-600">(Gemini · upload a reaction scheme image)</span>
        </div>
        <VisionPanel
          label="Analyze Image"
          busyLabel={t(lang, "btn.analyzing")}
          onAnalyze={async (file) => {
            setVisionData(null);
            setVisionData(await api.conditionsFromImage(file, lang));
          }}
        >
          {visionData && (
            <div className="space-y-2">
              <div className="text-xs text-gray-400 italic">{visionData.reaction_description}</div>
              {visionData.reaction_class_guess && (
                <div className="text-xs text-gray-300">
                  <span className="text-gray-500">Reaction class:</span>{" "}
                  {visionData.reaction_class_guess}
                </div>
              )}
              {visionData.candidates.length === 0 ? (
                <div className="text-xs text-gray-500">No conditions proposed.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="text-left text-gray-500">
                      <tr>
                        <th className="py-1 pr-3">#</th>
                        <th className="py-1 pr-3">Solvent</th>
                        <th className="py-1 pr-3">Catalyst</th>
                        <th className="py-1 pr-3">Base / Additive</th>
                        <th className="py-1 pr-3">Temp</th>
                        <th className="py-1 pr-3">Time</th>
                        <th className="py-1 pr-3">Conf.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visionData.candidates.map((c, i) => (
                        <tr key={i} className="border-t border-border align-top">
                          <td className="py-2 pr-3 text-gray-500">{i + 1}</td>
                          <td className="py-2 pr-3">{c.solvent || "—"}</td>
                          <td className="py-2 pr-3">{c.catalyst || "—"}</td>
                          <td className="py-2 pr-3">{c.base_or_additive || "—"}</td>
                          <td className="py-2 pr-3">{c.temperature || "—"}</td>
                          <td className="py-2 pr-3">{c.time || "—"}</td>
                          <td className="py-2 pr-3"><ConfidenceChip value={c.self_confidence} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="mt-2 space-y-1 text-xs text-gray-400">
                    {visionData.candidates.map((c, i) =>
                      c.rationale ? (
                        <div key={i}><span className="text-gray-500">#{i + 1}:</span> {c.rationale}</div>
                      ) : null,
                    )}
                  </div>
                </div>
              )}
              <div className="text-right text-[10px] text-gray-600">
                overall conf. {Math.round(visionData.overall_self_confidence * 100)}% ·{" "}
                {visionData.judge.model}
              </div>
            </div>
          )}
        </VisionPanel>
      </div>
    </div>
  );
}

function validate(bundle: NormBundle): string | null {
  if (!bundle.parsed)
    return "Enter a reaction in the top box. Format: reactants > reagents > products (e.g. CCO>>CC=O).";
  if (bundle.pending) return "Validating input…";
  if (bundle.parsed.kind !== "reaction") {
    return "Input is a single molecule, not a reaction. Use reaction SMILES with '>' separators, e.g. CCO>>CC=O or A.B>R>C.";
  }
  if (!bundle.reactant?.canonical_smiles) {
    return `Reactant side is not a valid SMILES: '${bundle.parsed.reactant}'. RDKit could not parse it.`;
  }
  if (!bundle.product?.canonical_smiles) {
    return `Product side is not a valid SMILES: '${bundle.parsed.product}'. RDKit could not parse it.`;
  }
  if (bundle.parsed.reagent && !bundle.reagent?.canonical_smiles) {
    return `Reagent side is not a valid SMILES: '${bundle.parsed.reagent}'. Leave the slot empty (use '>>') or fix the SMILES.`;
  }
  return null;
}
