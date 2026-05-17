"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { RetroResponse } from "@/lib/types";
import type { NormBundle } from "../MoleculeInput";
import { MoleculeRender } from "../MoleculeRender";
import { NarrativeBlock } from "../NarrativeBlock";
import { ResultBlock } from "../ResultBlock";

export function RetroTab({ bundle }: { bundle: NormBundle }) {
  const [data, setData] = useState<RetroResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Validation: this tab needs a single molecule target. Reaction → use product side.
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
      const r = await api.retro(target.canonical_smiles);
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
        {busy ? "Running…" : "Propose retrosynthesis"}
      </button>

      {err && (
        <div className="rounded border border-rose-700 bg-rose-900/30 p-3 text-sm text-rose-200">
          {err}
        </div>
      )}

      {data && !data.error && (
        <ResultBlock
          title="Retrosynthesis routes"
          confidence={data.confidence}
          verification={data.verification}
        >
          {data.routes.length === 0 ? (
            <div className="text-xs text-gray-500">No routes returned.</div>
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
