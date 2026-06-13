// English dictionary — the source of truth for translation keys.
// zh.ts must export the same shape (TypeScript enforces this via typeof en).

export const en = {
  "tab.fga": "Functional Groups",
  "tab.conditions": "Reaction Conditions",
  "tab.retro": "Retrosynthesis",

  "input.label": "Molecule or reaction (SMILES, InChI, MOL block, or A.B>R>C)",
  "input.placeholder": "CCO   |   CC(=O)O.CCO>>CCOC(=O)C   |   paste a MOL block",
  "input.invalid": "Invalid input — please check format",
  "input.checking": "checking…",
  "input.add_image": "📷 add image",
  "input.close_image": "✕ close image input",

  "btn.analyze": "Analyze",
  "btn.analyzing": "Analyzing…",
  "btn.analyze_fga": "Analyze functional groups",
  "btn.analyze_conditions": "Recommend conditions",
  "btn.analyze_retro": "Propose retrosynthesis",
  "btn.analyze_image": "Analyze Image",

  "confidence.high": "High confidence",
  "confidence.med": "Medium confidence",
  "confidence.low": "Low confidence",
  "confidence.composite": "Composite",

  "lang.toggle": "Language",

  "result.title.fga": "Functional group alert",
  "result.title.conditions": "Conditions",
  "result.title.retro": "Retrosynthesis routes",

  "result.generated_in": "generated in {{lang}}",
  "result.no_results": "(no results)",

  "retry.label": "Retried {{n}} time(s)",
  "ocr.not_verified": "OCR result not verified by round-trip",

  "narrative.toggle": "Raw LLM response",
  "narrative.thin_hint": "structured fields look sparse; showing raw output",

  "image.drop_hint": "📷 Drop a structure image · or paste (Ctrl/Cmd+V) · PNG/JPEG/WEBP ≤ 5 MB",
  "image.choose": "Choose file",
  "image.analyzing": "Analyzing image with Gemini…",
  "image.no_smiles": "Could not extract structure from image",
  "image.too_large": "image too large (max 5 MB)",
  "image.bad_type": "unsupported image type",
} as const;
