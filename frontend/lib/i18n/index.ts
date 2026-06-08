import { en } from "./en";
import { zh } from "./zh";

export type Lang = "en" | "zh";

// Use the keys from en but widen values to string so zh can have different text.
export type Key = keyof typeof en;
type Dict = Record<Key, string>;

const DICTS: Record<Lang, Dict> = { en, zh };

export function t(lang: Lang, key: Key, vars?: Record<string, string | number>): string {
  let s: string = DICTS[lang][key] ?? en[key];
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      s = s.replace(`{{${k}}}`, String(v));
    }
  }
  return s;
}

export { en, zh };
