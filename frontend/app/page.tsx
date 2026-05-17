"use client";

import { useState } from "react";
import { MoleculeInput, type NormBundle } from "@/components/MoleculeInput";
import { Tabs } from "@/components/Tabs";
import { ConditionsTab } from "@/components/tabs/ConditionsTab";
import { FGATab } from "@/components/tabs/FGATab";
import { RetroTab } from "@/components/tabs/RetroTab";

const TABS = [
  { id: "fga", label: "Functional Groups" },
  { id: "conditions", label: "Reaction Conditions" },
  { id: "retro", label: "Retrosynthesis" },
];

const EMPTY_BUNDLE: NormBundle = {
  reactant: null,
  reagent: null,
  product: null,
  single: null,
  parsed: null,
  pending: false,
};

export default function Page() {
  const [raw, setRaw] = useState("");
  const [active, setActive] = useState("fga");
  const [bundle, setBundle] = useState<NormBundle>(EMPTY_BUNDLE);

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">AI_chemist</h1>
        <p className="mt-1 text-sm text-gray-400">
          Generate → judge (LLM) → verify (RDKit/STOUT/OPSIN). LLM is a filter, not the source of truth.
        </p>
      </header>

      <section className="mb-8 rounded-lg border border-border bg-panel p-4">
        <MoleculeInput
          value={raw}
          onChange={setRaw}
          onNormalized={setBundle}
          testId="main-input"
        />
      </section>

      <Tabs tabs={TABS} active={active} onChange={setActive} />

      <section className="mt-6">
        {active === "fga" && <FGATab bundle={bundle} />}
        {active === "conditions" && <ConditionsTab bundle={bundle} />}
        {active === "retro" && <RetroTab bundle={bundle} />}
      </section>

      <footer className="mt-12 text-xs text-gray-500">
        Pipeline: SMILES↔IUPAC round-trip → LLM judgment → RDKit verification → composite confidence.
      </footer>
    </main>
  );
}
