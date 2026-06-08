import type { ReactNode } from "react";
import type { ConfidenceBreakdown, JudgeMeta, VerificationReport } from "@/lib/types";
import { useLang } from "./LanguageContext";
import { t } from "@/lib/i18n";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface Props {
  title: string;
  confidence: ConfidenceBreakdown;
  verification?: VerificationReport;
  judge?: JudgeMeta;
  outputLanguage?: string;
  children: ReactNode;
}

function RetryChip({ judge, lang }: { judge?: JudgeMeta; lang: "en" | "zh" }) {
  if (!judge) return null;
  const n = judge.retry_count ?? 0;
  const jr = judge.json_retry ?? false;
  if (n === 0 && !jr) return null;
  const label =
    n > 0 && jr
      ? `⟳ ${n} HTTP retry · JSON reprompt`
      : n > 0
        ? `⟳ ${n} HTTP retry${n > 1 ? "s" : ""}`
        : "⟳ JSON reprompt";
  return (
    <span
      title={t(lang, "retry.label", { n })}
      className="rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-mono text-amber-300"
    >
      {label}
    </span>
  );
}

export function ResultBlock({ title, confidence, verification, judge, outputLanguage, children }: Props) {
  const { lang } = useLang();
  const langLabel = outputLanguage && outputLanguage !== "en"
    ? t(lang, "result.generated_in", { lang: outputLanguage === "zh" ? "中文" : outputLanguage })
    : null;

  return (
    <div className="rounded-lg border border-border bg-panel p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-semibold tracking-wide text-gray-200">
          {title}
          <RetryChip judge={judge} lang={lang} />
          {langLabel && (
            <span className="rounded border border-border px-1.5 py-0.5 text-[10px] font-mono text-gray-500">
              {langLabel}
            </span>
          )}
        </h3>
        <ConfidenceBadge confidence={confidence} />
      </div>
      <div className="text-sm text-gray-300">{children}</div>
      {verification && verification.checks?.length > 0 && (
        <details className="mt-3 text-xs text-gray-400">
          <summary className="cursor-pointer">
            RDKit verification · pass rate {Math.round(verification.pass_rate * 100)}%
          </summary>
          <ul className="mt-2 space-y-1">
            {verification.checks.map((c, i) => (
              <li key={i} className="flex gap-2">
                <span className={c.passed ? "text-emerald-400" : "text-rose-400"}>
                  {c.passed ? "✓" : "✗"}
                </span>
                <span className="font-mono">{c.name}</span>
                {c.detail && <span className="text-gray-500">— {c.detail}</span>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
