"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { RetroResponse, VisionRetroResponse } from "@/lib/types";
import { useLang } from "@/components/LanguageContext";
import { t } from "@/lib/i18n";
import type { NormBundle } from "../MoleculeInput";
import { MoleculeRender } from "../MoleculeRender";
import { NarrativeBlock } from "../NarrativeBlock";
import { ResultBlock } from "../ResultBlock";
import { VisionPanel, ConfidenceChip } from "../VisionPanel";

export function RetroTab({ bundle }: { bundle: NormBundle }) {
  const [data, setData] = useState<RetroResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [visionData, setVisionData] = useState<VisionRetroResponse | null>(null);
  const { lang } = useLang();

  const target =
    bundle.parsed?.kind === "molecule"
      ? bundle.single
      : bundle.parsed?.kind === "reaction"
        ? bundle.product
        : null;

  const inputErr = validate(bundle, target);

  async function run() {
    if (inputErr || !target) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await api.retro(target.canonical_smiles, lang);
      setData(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {inputErr && (
        <div className="rounded border border-amber-700 bg-amber-900/20 p-3 text-sm text-amber-200">
          {inputErr}
        </div>
      )}
      {bundle.parsed?.kind === "reaction" && !inputErr && (
        <div className="rounded border border-border bg-panel p-2 text-xs text-gray-400">
          Reaction detected — retrosynthesis target = <span className="text-gray-200">product</span>:{" "}
          <span className="font-mono text-gray-200">{target?.canonical_smiles}</span>
        </div>
      )}

      <button
        onClick={run}
        disabled={busy || !!inputErr}
        data-testid="run-retro"
        className="rounded bg-accent px-4 py-2 text-sm font-semibold text-bg disabled:opacity-50"
      >
        {busy ? t(lang, "btn.analyzing") : t(lang, "btn.analyze_retro")}
      </button>

      {err && (
        <div className="rounded border border-rose-700 bg-rose-900/30 p-3 text-sm text-rose-200">
          {err}
        </div>
      )}

      {data && !data.error && (
        <ResultBlock
          title={t(lang, "result.title.retro")}
          confidence={data.confidence}
          verification={data.verification}
          judge={data.judge}
          outputLanguage={data.output_language}
        >
          {data.routes.length === 0 ? (
            <div className="text-xs text-gray-500">{t(lang, "result.no_results")}</div>
          ) : (
            <ol className="space-y-4" data-testid="retro-routes">
              {data.routes.map((r, i) => (
                <li key={i} className="rounded border border-border bg-bg p-3">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-gray-500">Route {i + 1}</span>
                    {r.name && <span className="text-sm font-semibold">{r.name}</span>}
                    {r.score !== undefined && (
                      <span className="ml-auto font-mono text-xs text-gray-400">
                        score {(r.score as number).toFixed?.(2)}
                      </span>
                    )}
                  </div>
                  {r.disconnection && (
                    <div className="text-xs text-gray-400">
                      <span className="text-gray-500">disconnection:</span> {r.disconnection}
                    </div>
                  )}
                  {r.rationale && <div className="mt-1 text-xs text-gray-400">{r.rationale}</div>}

                  {r.steps && r.steps.length > 0 && (
                    <ol className="mt-3 space-y-3 text-xs text-gray-300">
                      {r.steps.map((s, j) => {
                        const transform = s.transform || s.reaction;
                        const smi = s.intermediate_smiles || s.smiles;
                        const rationale = s.rationale || s.note;
                        return (
                          <li
                            key={j}
                            className="flex flex-col gap-2 rounded border border-border bg-panel p-2 md:flex-row"
                          >
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-gray-500">Step {s.step ?? j + 1}</span>
                                {transform && <strong className="text-sm">{transform}</strong>}
                                {typeof s.self_confidence === "number" && (
                                  <span className="ml-auto font-mono text-[10px] text-gray-500">
                                    self_conf {s.self_confidence.toFixed(2)}
                                  </span>
                                )}
                              </div>
                              {smi && (
                                <div className="mt-1 font-mono text-[11px] text-gray-200 break-all">
                                  {smi}
                                </div>
                              )}
                              {rationale && (
                                <div className="mt-1 text-xs text-gray-400">{rationale}</div>
                              )}
                            </div>
                            {smi && <MoleculeRender smiles={smi} width={200} height={150} />}
                          </li>
                        );
                      })}
                    </ol>
                  )}
                </li>
              ))}
            </ol>
          )}

          <NarrativeBlock
            narrative={data.narrative}
            thin={
              data.routes.length === 0 ||
              data.routes.every((r) => !r.steps || r.steps.length === 0)
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
          Direct Image Analysis <span className="normal-case text-gray-600">(Gemini · no SMILES required)</span>
        </div>
        <VisionPanel
          label="Analyze Image"
          busyLabel={t(lang, "btn.analyzing")}
          onAnalyze={async (file) => {
            setVisionData(null);
            setVisionData(await api.retroFromImage(file, lang));
          }}
        >
          {visionData && (
            <div className="space-y-2">
              <div className="text-xs text-gray-400 italic">{visionData.structure_description}</div>
              {visionData.routes.length === 0 ? (
                <div className="text-xs text-gray-500">No routes proposed.</div>
              ) : (
                <ol className="space-y-3">
                  {visionData.routes.map((r, i) => (
                    <li key={i} className="rounded border border-border bg-bg p-3">
                      <div className="mb-1 flex items-center gap-2">
                        <span className="text-gray-500 text-xs">Route {i + 1}</span>
                        <span className="text-sm font-semibold">{r.name}</span>
                        <ConfidenceChip value={r.self_confidence} />
                      </div>
                      <ol className="mt-2 space-y-2 text-xs">
                        {(r.steps ?? []).map((s, j) => (
                          <li key={j} className="flex gap-2 rounded border border-border bg-panel p-2">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-gray-500">Step {s.step}</span>
                                <strong>{s.transform}</strong>
                              </div>
                              {s.intermediate_smiles && (
                                <div className="mt-0.5 font-mono text-[11px] text-gray-300 break-all">
                                  {s.intermediate_smiles}
                                </div>
                              )}
                              <div className="mt-0.5 text-gray-400">{s.rationale}</div>
                            </div>
                            {s.intermediate_smiles && (
                              <MoleculeRender smiles={s.intermediate_smiles} width={140} height={110} />
                            )}
                          </li>
                        ))}
                      </ol>
                    </li>
                  ))}
                </ol>
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

function validate(
  bundle: NormBundle,
  target: { canonical_smiles: string } | null,
): string | null {
  if (!bundle.parsed) return "Enter a target molecule in the top box (SMILES, InChI, or MOL block).";
  if (bundle.pending) return "Validating input…";
  if (!target) return "Could not parse target.";
  if (!target.canonical_smiles) {
    return "Target is not a valid molecule. Check the SMILES/InChI/MOL block — RDKit could not parse it.";
  }
  return null;
}
