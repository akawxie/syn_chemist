"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { parseInput, type ParsedInput } from "@/lib/parseInput";
import type { NormalizedMolecule } from "@/lib/types";
import { MoleculeRender } from "./MoleculeRender";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onParsed?: (parsed: ParsedInput | null) => void;
  onNormalized?: (bundle: NormBundle) => void;
  label?: string;
  placeholder?: string;
  testId?: string;
}

export interface NormBundle {
  reactant: NormalizedMolecule | null;
  reagent: NormalizedMolecule | null;
  product: NormalizedMolecule | null;
  single: NormalizedMolecule | null;
  parsed: ParsedInput | null;
  pending: boolean;
}

const EMPTY: NormBundle = {
  reactant: null,
  reagent: null,
  product: null,
  single: null,
  parsed: null,
  pending: false,
};

export function MoleculeInput({
  value,
  onChange,
  onParsed,
  onNormalized,
  label = "Molecule or reaction (SMILES, InChI, MOL block, or A.B>R>C)",
  placeholder = "CCO   |   CC(=O)O.CCO>>CCOC(=O)C   |   paste a MOL block",
  testId,
}: Props) {
  const [bundle, setBundle] = useState<NormBundle>(EMPTY);

  useEffect(() => {
    const parsed = parseInput(value);
    onParsed?.(parsed);
    if (!parsed) {
      const next = { ...EMPTY };
      setBundle(next);
      onNormalized?.(next);
      return;
    }
    let cancelled = false;
    const t = setTimeout(async () => {
      const pendingBundle = { ...EMPTY, parsed, pending: true };
      setBundle(pendingBundle);
      onNormalized?.(pendingBundle);
      try {
        let next: NormBundle;
        if (parsed.kind === "molecule") {
          const n = await api.normalize(parsed.value);
          next = { ...EMPTY, single: n, parsed };
        } else {
          const [r, ag, p] = await Promise.all([
            api.normalize(parsed.reactant),
            parsed.reagent ? api.normalize(parsed.reagent) : Promise.resolve(null),
            api.normalize(parsed.product),
          ]);
          next = { reactant: r, reagent: ag, product: p, single: null, parsed, pending: false };
        }
        if (!cancelled) {
          setBundle(next);
          onNormalized?.(next);
        }
      } catch {
        if (!cancelled) {
          const next = { ...EMPTY, parsed };
          setBundle(next);
          onNormalized?.(next);
        }
      }
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const isReaction = bundle.parsed?.kind === "reaction";
  const pending = bundle.pending;

  return (
    <div className="flex flex-col gap-3">
      <div>
        <label className="mb-1 block text-xs uppercase tracking-wide text-gray-400">
          {label}
        </label>
        <textarea
          data-testid={testId}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={value.includes("\n") ? Math.min(12, value.split("\n").length) : 1}
          className="w-full resize-y rounded border border-border bg-panel px-3 py-2 font-mono text-sm text-gray-100 outline-none focus:border-accent"
        />
        <div className="mt-2 text-xs text-gray-400">{pending && "checking…"}</div>
      </div>

      {!isReaction && bundle.single && (
        <div className="flex flex-col gap-4 md:flex-row">
          <div className="flex-1 space-y-1 text-xs">
            <Row k="canonical" v={bundle.single.canonical_smiles || "—"} mono />
            <Row k="IUPAC" v={bundle.single.iupac ?? "—"} />
            <RoundTripRow n={bundle.single} />
          </div>
          <MoleculeRender smiles={bundle.single.canonical_smiles ?? ""} />
        </div>
      )}

      {isReaction && (
        <div className="space-y-3">
          <ReactionRow tag="REACTANT" n={bundle.reactant} />
          {bundle.reagent && <ReactionRow tag="REAGENT / CATALYST" n={bundle.reagent} />}
          <ReactionRow tag="PRODUCT" n={bundle.product} />
        </div>
      )}
    </div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div>
      <span className="text-gray-500">{k}:</span>{" "}
      <span className={mono ? "font-mono text-gray-200" : "text-gray-200"}>{v}</span>
    </div>
  );
}

function RoundTripRow({ n }: { n: NormalizedMolecule }) {
  return (
    <div>
      <span className="text-gray-500">round-trip:</span>{" "}
      <span className={n.round_trip_ok ? "text-emerald-400" : "text-amber-400"}>
        {n.round_trip_ok ? "ok" : `partial (${Math.round(n.round_trip_score * 100)}%)`}
      </span>
    </div>
  );
}

function ReactionRow({ tag, n }: { tag: string; n: NormalizedMolecule | null }) {
  if (!n) {
    return (
      <div className="rounded border border-border bg-bg p-2 text-xs text-gray-500">
        {tag}: (empty)
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3 rounded border border-border bg-bg p-3 md:flex-row">
      <div className="flex-1 space-y-1 text-xs">
        <div className="text-[10px] uppercase tracking-wide text-gray-500">{tag}</div>
        <Row k="canonical" v={n.canonical_smiles || "—"} mono />
        <Row k="IUPAC" v={n.iupac ?? "—"} />
        <RoundTripRow n={n} />
      </div>
      <MoleculeRender smiles={n.canonical_smiles ?? ""} width={260} height={180} />
    </div>
  );
}
