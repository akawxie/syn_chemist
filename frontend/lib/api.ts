import type {
  ConditionsResponse,
  FGAResponse,
  NormalizedMolecule,
  RetroResponse,
} from "./types";
import type { Lang } from "./i18n";

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

  fga: (input: string, lang: Lang = "en") =>
    post<FGAResponse>("/api/fga", { input, lang }),

  conditions: (
    reactant: string,
    product: string,
    opts?: {
      reagent?: string | null;
      reaction_class_hint?: string | null;
      lang?: Lang;
    },
  ) =>
    post<ConditionsResponse>("/api/conditions", {
      reactant,
      product,
      reagent: opts?.reagent || null,
      reaction_class_hint: opts?.reaction_class_hint || null,
      lang: opts?.lang ?? "en",
    }),

  retro: (target: string, lang: Lang = "en") =>
    post<RetroResponse>("/api/retro", { target, lang }),

  moleculeFromImage: async (file: File): Promise<ImageOCRResponse> => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/api/molecule/from_image`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      let message = text;
      try {
        const parsed = JSON.parse(text) as { detail?: string };
        if (parsed.detail) message = parsed.detail;
      } catch {
        /* not JSON */
      }
      throw new Error(`${res.status}: ${message || res.statusText}`);
    }
    return res.json() as Promise<ImageOCRResponse>;
  },
};

export interface ImageOCRResponse {
  smiles: string;
  ocr_raw: string;
  canonical_smiles: string;
  iupac: string | null;
  round_trip_ok: boolean;
  round_trip_score: number;
  notes: string[];
  warning?: string | null;
}
