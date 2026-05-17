import type {
  ConditionsResponse,
  FGAResponse,
  NormalizedMolecule,
  RetroResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  normalize: (input: string) =>
    post<NormalizedMolecule>("/api/molecule/normalize", { input }),
  fga: (input: string) => post<FGAResponse>("/api/fga", { input }),
  conditions: (
    reactant: string,
    product: string,
    opts?: { reagent?: string | null; reaction_class_hint?: string | null },
  ) =>
    post<ConditionsResponse>("/api/conditions", {
      reactant,
      product,
      reagent: opts?.reagent || null,
      reaction_class_hint: opts?.reaction_class_hint || null,
    }),
  retro: (target: string) => post<RetroResponse>("/api/retro", { target }),
};
