"use client";

// Always-available raw LLM output. JSON output sometimes squeezes most useful
// content into one prose field; the structured table can look empty even when
// the model said useful things. So we surface the raw response too.
//
// Heuristic: if the caller says structured content is "thin", we open by default;
// otherwise collapsed.

interface Props {
  narrative?: string;
  thin?: boolean;        // when true, open by default
  title?: string;
}

export function NarrativeBlock({ narrative, thin = false, title = "Raw LLM response" }: Props) {
  if (!narrative || !narrative.trim()) return null;

  // Try to pretty-print JSON; if not JSON, keep as-is.
  let pretty = narrative.trim();
  try {
    const obj = JSON.parse(pretty);
    pretty = JSON.stringify(obj, null, 2);
  } catch {
    // not JSON — leave as plain text
  }

  return (
    <details open={thin} className="mt-3 rounded border border-border bg-bg p-2 text-xs">
      <summary className="cursor-pointer text-gray-400">
        {title}
        {thin && (
          <span className="ml-2 text-amber-300">
            · structured fields look sparse; showing raw output
          </span>
        )}
      </summary>
      <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-gray-300">
        {pretty}
      </pre>
    </details>
  );
}
