// Parse the top-level input. Accepts:
//   - Single molecule: SMILES / InChI / MOL block
//   - Reaction SMILES: "A.B>R>C" or "A.B>>C" (reactants > agents > products)

export type ParsedInput =
  | { kind: "molecule"; value: string }
  | { kind: "reaction"; reactant: string; reagent: string | null; product: string };

export function parseInput(raw: string): ParsedInput | null {
  const text = raw.trim();
  if (!text) return null;

  // Reaction SMILES has exactly two `>` separators (one or both sides can be empty).
  // We require the input to be a single line for reaction parsing — MOL blocks are
  // multi-line and shouldn't be misread.
  if (!text.includes("\n") && (text.match(/>/g) || []).length >= 2) {
    const parts = text.split(">");
    if (parts.length === 3) {
      const [reactant, reagent, product] = parts;
      if (reactant && product) {
        return {
          kind: "reaction",
          reactant: reactant.trim(),
          reagent: reagent.trim() ? reagent.trim() : null,
          product: product.trim(),
        };
      }
    }
  }
  return { kind: "molecule", value: text };
}
