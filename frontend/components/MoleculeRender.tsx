"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  smiles: string;
  width?: number;
  height?: number;
}

export function MoleculeRender({ smiles, width = 360, height = 240 }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function draw() {
      if (!smiles || !hostRef.current) return;
      setErr(null);
      try {
        const mod = await import("smiles-drawer");
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const SD: any = (mod as any).default ?? mod;
        const smiDrawer = new SD.SmiDrawer(
          { width, height, padding: 12 },
          {},
        );
        const svg = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "svg",
        );
        svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.setAttribute("width", String(width));
        svg.setAttribute("height", String(height));
        smiDrawer.draw(
          smiles,
          svg,
          "dark",
          () => {
            if (cancelled || !hostRef.current) return;
            hostRef.current.replaceChildren(svg);
          },
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (e: any) => {
            if (!cancelled) setErr(String(e?.message ?? e));
          },
        );
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      }
    }
    draw();
    return () => {
      cancelled = true;
    };
  }, [smiles, width, height]);

  if (!smiles) {
    return (
      <div
        className="flex items-center justify-center rounded border border-border bg-panel text-sm text-gray-500"
        style={{ width, height }}
      >
        no structure
      </div>
    );
  }

  return (
    <div
      ref={hostRef}
      className="flex items-center justify-center rounded border border-border bg-panel overflow-hidden"
      style={{ width, height }}
      data-testid="molecule-render"
    >
      {err && <span className="px-2 text-xs text-rose-400">render error: {err}</span>}
    </div>
  );
}
