// Mirrors backend pydantic / dataclass outputs. Hand-written; keep in sync with
// backend/app/pipeline/{naming,confidence,verify}.py and backend/app/modules/*.

export interface NormalizedMolecule {
  input_raw: string;
  canonical_smiles: string;
  iupac: string | null;
  round_trip_ok: boolean;
  round_trip_score: number;
  notes: string[];
}

export interface ConfidenceBreakdown {
  composite: number;
  round_trip?: number;
  judge?: number;
  verify?: number;
  weights?: { round_trip: number; judge: number; verify: number };
}

export interface VerificationReport {
  pass_rate: number;
  checks: Array<{ name: string; passed: boolean; detail?: string }>;
}

export interface JudgeMeta {
  provider: string;
  model: string;
  retry_count?: number;
  json_retry?: boolean;
}

export interface DetectedGroup {
  name: string;
  smarts?: string;
  count: number;
}

export interface FGAAlert {
  group: string;
  severity?: string;
  risk?: string;
  reason?: string;
  smarts?: string;
  self_confidence?: number;
  [k: string]: unknown;
}

export interface FragmentHit {
  name: string;
  count: number;
}

export interface FGAResponse {
  module: "fga";
  input: string;
  normalized: NormalizedMolecule;
  detected_groups: DetectedGroup[];
  fragments: FragmentHit[];
  alerts: FGAAlert[];
  narrative?: string;
  verification: VerificationReport;
  confidence: ConfidenceBreakdown;
  judge: JudgeMeta;
  output_language?: string;
  error?: string;
  notes?: string[];
}

export interface ConditionCandidate {
  solvent?: string;
  catalyst?: string;
  temperature?: string;
  time?: string;
  equivalents?: string;
  rationale?: string;
  score?: number;
  [k: string]: unknown;
}

export interface ConditionsResponse {
  module: "conditions";
  reactant: NormalizedMolecule;
  product: NormalizedMolecule;
  reagent?: NormalizedMolecule | null;
  reaction_class_guess: string | null;
  candidates: ConditionCandidate[];
  narrative?: string;
  verification: VerificationReport;
  confidence: ConfidenceBreakdown;
  judge: JudgeMeta;
  output_language?: string;
  error?: string;
}

export interface RetroStep {
  step?: number;
  transform?: string;       // reaction class (e.g. "Amide coupling")
  intermediate_smiles?: string;
  rationale?: string;
  self_confidence?: number;
  // Tolerate alternative field names some LLMs use:
  reaction?: string;
  smiles?: string;
  note?: string;
}

export interface RetroRoute {
  name?: string;
  disconnection?: string;
  steps?: RetroStep[];
  intermediates?: string[];  // optional top-level summary (not always present)
  rationale?: string;
  score?: number;
  self_confidence?: number;
  [k: string]: unknown;
}

export interface RetroResponse {
  module: "retro";
  target: NormalizedMolecule;
  detected_groups: DetectedGroup[];
  routes: RetroRoute[];
  narrative?: string;
  verification: VerificationReport;
  confidence: ConfidenceBreakdown;
  judge: JudgeMeta;
  output_language?: string;
  error?: string;
}
