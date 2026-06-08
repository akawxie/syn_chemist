"use client";

import { useState } from "react";
import type { ConfidenceBreakdown } from "@/lib/types";
import { useLang } from "./LanguageContext";
import { t as i18n } from "@/lib/i18n";

function tone(score: number, lang: "en" | "zh"): { label: string; cls: string } {
  if (score >= 0.75) return { label: i18n(lang, "confidence.high"), cls: "bg-emerald-600/30 text-emerald-300 border-emerald-700" };
  if (score >= 0.5) return { label: i18n(lang, "confidence.med"), cls: "bg-amber-600/30 text-amber-200 border-amber-700" };
  return { label: i18n(lang, "confidence.low"), cls: "bg-rose-600/30 text-rose-200 border-rose-700" };
}

export function ConfidenceBadge({ confidence }: { confidence: ConfidenceBreakdown }) {
  const [open, setOpen] = useState(false);
  const { lang } = useLang();
  const pct = Math.round((confidence.composite ?? 0) * 100);
  const tn = tone(confidence.composite ?? 0, lang);
  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`rounded border px-2 py-1 text-xs font-mono ${tn.cls}`}
        aria-expanded={open}
        data-testid="confidence-badge"
      >
        {i18n(lang, "confidence.composite")} {pct}% · {tn.label}
      </button>
      {open && (
        <div className="absolute z-10 mt-1 w-64 rounded border border-border bg-panel p-3 text-xs shadow-lg">
          <div className="mb-2 font-semibold text-gray-200">Breakdown</div>
          <Row k="round-trip" v={confidence.round_trip} w={confidence.weights?.round_trip} />
          <Row k="judge" v={confidence.judge} w={confidence.weights?.judge} />
          <Row k="verify" v={confidence.verify} w={confidence.weights?.verify} />
          <div className="mt-2 border-t border-border pt-2 text-gray-400">
            Composite is a weighted average. LLM is judge, not source of truth.
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ k, v, w }: { k: string; v?: number; w?: number }) {
  if (v === undefined) return null;
  return (
    <div className="flex justify-between text-gray-300">
      <span>{k}{w !== undefined ? ` (w=${w})` : ""}</span>
      <span className="font-mono">{(v * 100).toFixed(0)}%</span>
    </div>
  );
}
