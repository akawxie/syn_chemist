"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type ImageOCRResponse } from "@/lib/api";
import { useLang } from "./LanguageContext";
import { t } from "@/lib/i18n";

const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED = new Set(["image/png", "image/jpeg", "image/webp"]);

interface Props {
  onSmilesDetected: (smiles: string, warning?: string | null) => void;
}

type State =
  | { kind: "idle" }
  | { kind: "preview"; src: string; name: string }
  | { kind: "uploading"; src: string }
  | { kind: "result"; src: string; data: ImageOCRResponse }
  | { kind: "error"; message: string };

export function ImageInput({ onSmilesDetected }: Props) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const inputRef = useRef<HTMLInputElement | null>(null);
  const dropRef = useRef<HTMLDivElement | null>(null);
  const { lang } = useLang();

  const handleFile = useCallback(
    async (file: File) => {
      if (!ALLOWED.has(file.type)) {
        setState({ kind: "error", message: t(lang, "image.bad_type") });
        return;
      }
      if (file.size > MAX_BYTES) {
        setState({ kind: "error", message: t(lang, "image.too_large") });
        return;
      }
      const src = URL.createObjectURL(file);
      setState({ kind: "uploading", src });
      try {
        const data = await api.moleculeFromImage(file);
        setState({ kind: "result", src, data });
        if (data.smiles) {
          onSmilesDetected(data.smiles, data.warning);
        }
      } catch (err) {
        setState({ kind: "error", message: (err as Error).message });
      }
    },
    [onSmilesDetected],
  );

  // Paste handler — global so user doesn't have to focus an exact element
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      if (!e.clipboardData) return;
      const target = dropRef.current;
      if (!target) return;
      // Only intercept when the drop zone is the closest "interesting" target —
      // i.e. our component is visible. Cheap check: bounding rect non-zero.
      const rect = target.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;
      for (const item of Array.from(e.clipboardData.items)) {
        if (item.kind === "file") {
          const f = item.getAsFile();
          if (f) {
            e.preventDefault();
            void handleFile(f);
            return;
          }
        }
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [handleFile]);

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) void handleFile(f);
  };

  return (
    <div
      ref={dropRef}
      onDrop={onDrop}
      onDragOver={(e) => e.preventDefault()}
      className="rounded border border-dashed border-border bg-panel/50 p-3 text-xs"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-gray-400">
          {t(lang, "image.drop_hint")}
        </span>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="rounded border border-border px-2 py-1 text-gray-200 hover:bg-bg"
        >
          {t(lang, "image.choose")}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleFile(f);
            e.target.value = "";
          }}
        />
      </div>

      {state.kind === "uploading" && (
        <div className="mt-3 flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={state.src} alt="uploading" className="h-20 w-20 rounded border border-border object-contain" />
          <span className="text-gray-400">{t(lang, "image.analyzing")}</span>
        </div>
      )}

      {state.kind === "result" && (
        <div className="mt-3 flex items-start gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={state.src} alt="uploaded" className="h-20 w-20 rounded border border-border object-contain" />
          <div className="flex-1 space-y-1">
            {state.data.smiles ? (
              <>
                <div>
                  <span className="text-gray-500">SMILES:</span>{" "}
                  <span className="font-mono text-emerald-300">{state.data.smiles}</span>
                </div>
                {state.data.iupac && (
                  <div>
                    <span className="text-gray-500">IUPAC:</span>{" "}
                    <span className="text-gray-200">{state.data.iupac}</span>
                  </div>
                )}
                {state.data.warning && (
                  <div className="text-amber-300">⚠ {state.data.warning}</div>
                )}
              </>
            ) : (
              <div className="text-amber-300">
                ⚠ {state.data.warning || t(lang, "image.no_smiles")}
              </div>
            )}
          </div>
        </div>
      )}

      {state.kind === "error" && (
        <div className="mt-3 rounded border border-rose-500/40 bg-rose-500/10 p-2 text-rose-300">
          ✗ {state.message}
        </div>
      )}
    </div>
  );
}
