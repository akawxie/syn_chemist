import type { ReactNode } from "react";
import type { ConfidenceBreakdown, VerificationReport } from "@/lib/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface Props {
  title: string;
  confidence: ConfidenceBreakdown;
  verification?: VerificationReport;
  children: ReactNode;
}

export function ResultBlock({ title, confidence, verification, children }: Props) {
  return (
    <div className="rounded-lg border border-border bg-panel p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold tracking-wide text-gray-200">{title}</h3>
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
