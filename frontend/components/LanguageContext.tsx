"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { t, type Key, type Lang } from "@/lib/i18n";

interface Ctx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: Key, vars?: Record<string, string | number>) => string;
}

const LanguageContext = createContext<Ctx | null>(null);
const STORAGE_KEY = "ai_chemist_lang";

function detectInitial(): Lang {
  if (typeof window === "undefined") return "en";
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "zh") return stored;
    if (navigator.language?.toLowerCase().startsWith("zh")) return "zh";
  } catch {
    /* ignore */
  }
  return "en";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  // Defer to client-only on mount to avoid SSR/CSR mismatch
  useEffect(() => {
    setLangState(detectInitial());
  }, []);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      window.localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* ignore quota / private mode */
    }
  }, []);

  const value = useMemo<Ctx>(
    () => ({ lang, setLang, t: (k, v) => t(lang, k, v) }),
    [lang, setLang],
  );
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLang(): Ctx {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    // Fallback for component trees not wrapped in Provider (e.g. unit tests)
    return { lang: "en", setLang: () => {}, t: (k, v) => t("en", k, v) };
  }
  return ctx;
}
