"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { FGAResponse } from "@/lib/types";
import { useLang } from "@/components/LanguageContext";
import { t } from "@/lib/i18n";
import type { NormBundle } from "../MoleculeInput";
import { NarrativeBlock } from "../NarrativeBlock";
import { ResultBlock } from "../ResultBlock";

export function FGATab({ bundle }: { bundle: NormBundle }) {
  const [data, setData] = useState<FGAResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
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
      const r = await api.fga(target.canonical_smiles, lang);
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
          Reaction detected — analyzing the <span className="text-gray-200">product</span> side:{" "}
          <span className="font-mono text-gray-200">{target?.canonical_smiles}</span>
        </div>
      )}

      <button
        onClick={run}
        disabled={busy || !!inputErr}
        data-testid="run-fga"
        className="rounded bg-accent px-4 py-2 text-sm font-semibold text-bg disabled:opacity-50"
      >
        {busy ? t(lang, "btn.analyzing") : t(lang, "btn.analyze_fga")}
      </button>

      {err && (
        <div className="rounded border border-rose-700 bg-rose-900/30 p-3 text-sm text-rose-200">
          {err}
        </div>
      )}

      {data && !data.error && (
        <ResultBlock
          title={t(lang, "result.title.fga")}
          confidence={data.confidence}
          verification={data.verification}
          judge={data.judge}
          outputLanguage={data.output_language}
        >
          <div className="mb-3">
            <div className="text-xs uppercase tracking-wide text-gray-500">
              Hazard-tagged groups (curated SMARTS)
            </div>
            <ul className="mt-1 flex flex-wrap gap-2">
              {data.detected_groups.map((g, i) => (
                <li key={i} className="rounded border border-border bg-bg px-2 py-0.5 text-xs">
                  {g.name} <span className="text-gray-500">×{g.count}</span>
                </li>
              ))}
              {data.detected_groups.length === 0 && (
                <li className="text-xs text-gray-500">none</li>
              )}
            </ul>
          </div>

          {data.fragments && data.fragments.length > 0 && (
            <details className="mb-3 text-xs">
              <summary className="cursor-pointer text-gray-500">
                RDKit fragment inventory ({data.fragments.length})
              </summary>
              <ul className="mt-2 flex flex-wrap gap-2">
                {data.fragments.map((f, i) => (
                  <li key={i} className="rounded border border-border bg-bg px-2 py-0.5 text-xs text-gray-300">
                    {f.name} <span className="text-gray-500">×{f.count}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}

          <div>
            <div className="text-xs uppercase tracking-wide text-gray-500">LLM alerts</div>
            {data.alerts.length === 0 ? (
              <div className="mt-1 text-xs text-gray-500">No alerts.</div>
            ) : (
              <ul className="mt-1 space-y-2" data-testid="fga-alerts">
                {data.alerts.map((a, i) => (
                  <li key={i} className="rounded border border-border bg-bg p-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{a.group}</span>
                      {a.severity && (
                        <span className="text-xs uppercase text-amber-300">{a.severity}</span>
                      )}
                      {a.smarts && (
                        <span
                          className="ml-auto font-mono text-[10px] text-gray-500"
                          title="LLM-supplied SMARTS, verified by RDKit"
                        >
                          smarts: {a.smarts}
                        </span>
                      )}
                    </div>
                    {(a.risk || a.reason) && (
                      <div className="mt-1 text-xs text-gray-400">{a.risk || a.reason}</div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <NarrativeBlock narrative={data.narrative} thin={data.alerts.length === 0} />
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
  if (!bundle.parsed) return "Enter a molecule in the top box (SMILES, InChI, or MOL block).";
  if (bundle.pending) return "Validating input…";
  if (!target) return "Could not parse molecule.";
  if (!target.canonical_smiles) {
    return "Input is not a valid molecule. Check the SMILES/InChI/MOL block — RDKit could not parse it.";
  }
  return null;
}
