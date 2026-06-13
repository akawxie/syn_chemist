"use client";

import { useCallback, useRef, useState } from "react";

const ALLOWED = new Set(["image/png", "image/jpeg", "image/webp"]);
const MAX_BYTES = 5 * 1024 * 1024;

interface Props {
  /** Label for the analyse button */
  label: string;
  busyLabel: string;
  /** Called with the validated File; caller owns async state */
  onAnalyze: (file: File) => Promise<void>;
  children?: React.ReactNode;
}

export function VisionPanel({ label, busyLabel, onAnalyze, children }: Props) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handle = useCallback(
    async (file: File) => {
      if (!ALLOWED.has(file.type)) {
        setErr("Unsupported format — use PNG, JPEG, or WEBP.");
        return;
      }
      if (file.size > MAX_BYTES) {
        setErr("Image too large (max 5 MB).");
        return;
      }
      setErr(null);
      setPreview(URL.createObjectURL(file));
      setBusy(true);
      try {
        await onAnalyze(file);
      } catch (e) {
        setErr(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [onAnalyze],
  );

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) void handle(f);
  };

  return (
    <div className="space-y-3 rounded border border-dashed border-border bg-panel/40 p-3">
      <div className="flex items-center gap-3">
        {/* drop zone / preview */}
        <div
          onDrop={onDrop}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => !busy && inputRef.current?.click()}
          className="flex h-20 w-20 shrink-0 cursor-pointer items-center justify-center overflow-hidden rounded border border-border bg-bg text-xs text-gray-500 hover:border-accent"
        >
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="preview" className="h-full w-full object-contain" />
          ) : (
            <span className="text-center text-[10px] leading-tight text-gray-600">
              drop image<br />or click
            </span>
          )}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handle(f);
            e.target.value = "";
          }}
        />

        <div className="flex flex-col gap-2">
          <button
            onClick={() => inputRef.current?.click()}
            disabled={busy}
            className="rounded bg-accent px-3 py-1.5 text-sm font-semibold text-bg disabled:opacity-50"
          >
            {busy ? busyLabel : label}
          </button>
          <span className="text-[10px] text-gray-600">PNG / JPEG / WEBP · max 5 MB</span>
        </div>
      </div>

      {err && (
        <div className="rounded border border-rose-700 bg-rose-900/30 p-2 text-xs text-rose-200">
          {err}
        </div>
      )}

      {children}
    </div>
  );
}

/** Severity badge */
export function SeverityBadge({ severity }: { severity: string }) {
  const color =
    severity === "high"
      ? "text-rose-300 border-rose-700"
      : severity === "medium"
        ? "text-amber-300 border-amber-700"
        : "text-emerald-400 border-emerald-800";
  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase ${color}`}>
      {severity}
    </span>
  );
}

/** Small confidence chip */
export function ConfidenceChip({ value }: { value: number }) {
  return (
    <span className="ml-auto text-[10px] text-gray-500">
      {Math.round(value * 100)}% conf.
    </span>
  );
}
