// smiles-drawer 2.x ships no TypeScript declarations.
// We use it dynamically (`await import("smiles-drawer")`) and access its API via a typed-any
// shim; this file just stops `tsc` from failing on the implicit-any module resolution.
declare module "smiles-drawer";
