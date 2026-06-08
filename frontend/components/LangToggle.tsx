"use client";

import { useLang } from "./LanguageContext";

export function LangToggle() {
  const { lang, setLang } = useLang();
  const Btn = ({ value, label }: { value: "en" | "zh"; label: string }) => (
    <button
      type="button"
      onClick={() => setLang(value)}
      className={
        "px-2 py-0.5 text-xs " +
        (lang === value
          ? "bg-accent/20 text-accent"
          : "text-gray-400 hover:text-gray-200")
      }
    >
      {label}
    </button>
  );
  return (
    <div
      className="inline-flex overflow-hidden rounded border border-border"
      role="group"
      aria-label="language"
    >
      <Btn value="en" label="EN" />
      <Btn value="zh" label="中" />
    </div>
  );
}
