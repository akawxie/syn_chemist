"use client";

interface Tab {
  id: string;
  label: string;
}

interface Props {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
}

export function Tabs({ tabs, active, onChange }: Props) {
  return (
    <div role="tablist" className="flex gap-1 border-b border-border">
      {tabs.map((t) => {
        const selected = t.id === active;
        return (
          <button
            key={t.id}
            role="tab"
            aria-selected={selected}
            data-testid={`tab-${t.id}`}
            onClick={() => onChange(t.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm transition-colors ${
              selected
                ? "border-accent text-accent"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
