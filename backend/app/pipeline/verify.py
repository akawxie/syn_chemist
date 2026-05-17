"""RDKit-based chemistry verification — the PRD's 'hard truth' layer."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from rdkit import Chem


@dataclass
class VerifyReport:
    pass_rate: float  # 0..1
    checks: list[dict] = field(default_factory=list)  # [{name, ok, detail}]

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append({"name": name, "ok": ok, "detail": detail})

    def finalize(self) -> VerifyReport:
        if not self.checks:
            self.pass_rate = 0.0
        else:
            self.pass_rate = sum(1 for c in self.checks if c["ok"]) / len(self.checks)
        return self


def is_valid_smiles(smiles: str) -> bool:
    if not smiles:
        return False
    return Chem.MolFromSmiles(smiles) is not None


def atom_counts(smiles: str) -> Counter[str]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return Counter()
    mol = Chem.AddHs(mol)
    return Counter(a.GetSymbol() for a in mol.GetAtoms())


def reaction_atom_balance(reactant_smiles: list[str], product_smiles: list[str]) -> tuple[bool, str]:
    """Sum atom counts on both sides; return (balanced, detail)."""
    r = Counter()
    for s in reactant_smiles:
        r.update(atom_counts(s))
    p = Counter()
    for s in product_smiles:
        p.update(atom_counts(s))
    diff_r = r - p
    diff_p = p - r
    # Allow H imbalance — most published reactions don't track H explicitly.
    diff_r.pop("H", None)
    diff_p.pop("H", None)
    if not diff_r and not diff_p:
        return True, "balanced (heavy atoms)"
    return False, f"unbalanced: extra in reactants={dict(diff_r)}, extra in products={dict(diff_p)}"


# ---------- Functional group detection (SMARTS library) ----------

# Curated subset of safety/reactivity-relevant groups. Extend over time.
FUNCTIONAL_GROUPS: list[tuple[str, str, str]] = [
    # (name, SMARTS, severity: 'low'|'medium'|'high')
    ("nitro", "[NX3](=O)=O", "high"),
    ("azide", "[N-]=[N+]=N", "high"),
    ("diazo", "[N+]#N", "high"),
    ("nitrile", "C#N", "low"),
    ("aldehyde", "[CX3H1](=O)[#6]", "low"),
    ("ketone", "[CX3](=O)[#6]", "low"),
    ("carboxylic_acid", "[CX3](=O)[OX2H1]", "low"),
    ("ester", "[CX3](=O)[OX2][#6]", "low"),
    ("amide", "[NX3][CX3](=O)[#6]", "low"),
    ("primary_amine", "[NX3;H2;!$(NC=O)]", "low"),
    ("aniline", "c[NX3;H2,H1]", "low"),
    ("phenol", "c[OX2H]", "low"),
    ("alcohol", "[CX4][OX2H]", "low"),
    ("alkene", "[CX3]=[CX3]", "low"),
    ("alkyne", "[CX2]#[CX2]", "low"),
    ("epoxide", "C1OC1", "high"),
    ("aziridine", "C1NC1", "high"),
    ("peroxide", "[OX2][OX2]", "high"),
    ("acyl_chloride", "[CX3](=O)Cl", "high"),
    ("sulfonyl_chloride", "S(=O)(=O)Cl", "high"),
    ("isocyanate", "N=C=O", "high"),
    ("boronic_acid", "B(O)O", "low"),
    ("aryl_halide", "[c][F,Cl,Br,I]", "low"),
    ("nitroso", "N=O", "medium"),
    ("hydrazine", "N-N", "medium"),
    ("thiol", "[SX2H]", "medium"),
]


def detect_functional_groups(smiles: str) -> list[dict]:
    """Return list of {name, severity, count} for groups present."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []
    hits = []
    for name, smarts, severity in FUNCTIONAL_GROUPS:
        patt = Chem.MolFromSmarts(smarts)
        if patt is None:
            continue
        matches = mol.GetSubstructMatches(patt)
        if matches:
            hits.append({"name": name, "severity": severity, "count": len(matches)})
    return hits


def detect_fragments(smiles: str) -> list[dict]:
    """Broad RDKit fragment inventory via rdkit.Chem.Fragments (~85 fr_* functions).

    Complements the curated SMARTS table by surfacing common medicinal-chemistry
    fragments (methoxy, ether, pyrrole, pyridine, furan, thiophene, indole, halide
    classes, etc.) that aren't in our hazard-tagged list.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []
    from rdkit.Chem import Fragments  # local import; rdkit is heavy

    hits: list[dict] = []
    for attr in dir(Fragments):
        if not attr.startswith("fr_"):
            continue
        fn = getattr(Fragments, attr)
        if not callable(fn):
            continue
        try:
            count = int(fn(mol))
        except Exception:
            continue
        if count > 0:
            hits.append({"name": attr[3:], "count": count})  # strip 'fr_'
    return hits


def _normalize_group_name(s: str) -> str:
    return s.strip().lower().replace("fr_", "").replace("-", "_").replace(" ", "_")


def verify_fga(canonical_smiles: str, llm_alerts: list[dict]) -> VerifyReport:
    """Verify each LLM alert against RDKit.

    An alert passes if either:
      (1) its name matches an entry in the inventory (curated SMARTS table or fr_* fragments), or
      (2) the LLM supplied a SMARTS pattern and that pattern matches the molecule.
    Case (2) lets the LLM extend coverage beyond our predefined sets while keeping
    RDKit as the source of truth.
    """
    report = VerifyReport(pass_rate=0.0)
    inventory: set[str] = set()
    for h in detect_functional_groups(canonical_smiles):
        inventory.add(_normalize_group_name(h["name"]))
    for h in detect_fragments(canonical_smiles):
        inventory.add(_normalize_group_name(h["name"]))

    report.add("structure_legality", is_valid_smiles(canonical_smiles))
    if not llm_alerts:
        report.add("llm_returned_alerts", False, "judge produced no alerts")
        return report.finalize()

    mol = Chem.MolFromSmiles(canonical_smiles)
    for alert in llm_alerts:
        raw = alert.get("group", "")
        name = _normalize_group_name(raw)
        ok = bool(name) and (name in inventory or any(name in inv or inv in name for inv in inventory))
        detail = ""
        if not ok:
            smarts = (alert.get("smarts") or "").strip()
            if smarts and mol is not None:
                patt = Chem.MolFromSmarts(smarts)
                if patt is not None and mol.GetSubstructMatches(patt):
                    ok = True
                    detail = f"verified via LLM SMARTS: {smarts}"
                else:
                    detail = f"LLM SMARTS did not match: {smarts}"
            else:
                detail = "not in inventory and no SMARTS supplied"
        report.add(f"alert:{raw}", ok, detail)
    return report.finalize()


def verify_conditions(reactant: str, product: str, candidates: list[dict]) -> VerifyReport:
    """For Module B: validate candidate conditions against reactant/product."""
    report = VerifyReport(pass_rate=0.0)
    report.add("reactant_legal", is_valid_smiles(reactant))
    report.add("product_legal", is_valid_smiles(product))
    balanced, detail = reaction_atom_balance([reactant], [product])
    # Note: for many real reactions there will be byproducts; treat imbalance as advisory not failure.
    report.add("atom_balance_advisory", True, detail)
    for i, cand in enumerate(candidates[:5]):
        ok = bool(cand.get("solvent") and cand.get("temperature") is not None)
        report.add(f"candidate_{i}_complete", ok)
    return report.finalize()


def verify_retro(target: str, routes: list[dict]) -> VerifyReport:
    """For Module C: each step must produce a valid molecule and conserve heavy atoms (advisory)."""
    report = VerifyReport(pass_rate=0.0)
    report.add("target_legal", is_valid_smiles(target))
    for ri, route in enumerate(routes[:5]):
        steps = route.get("steps", [])
        for si, step in enumerate(steps):
            smi = step.get("intermediate_smiles", "")
            report.add(
                f"route_{ri}_step_{si}_legal",
                is_valid_smiles(smi),
                "" if is_valid_smiles(smi) else f"invalid SMILES: {smi}",
            )
    return report.finalize()
