import { useEffect, useId, useRef, useState } from "react";
import type { DisplayStatus } from "../types";
import { StatusBadge } from "./StatusBadge";

export type FilterGroup = {
  id: string;
  label: string;
  options: { id: string; label: string; tone?: DisplayStatus }[];
};

type Props = {
  groups: FilterGroup[];
  selected: Record<string, string[]>;
  onApply: (next: Record<string, string[]>) => void;
  onClear: () => void;
  activeCount: number;
};

export function FilterPopover({
  groups,
  selected,
  onApply,
  onClear,
  activeCount,
}: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(selected);
  const rootRef = useRef<HTMLDivElement>(null);
  const labelId = useId();

  useEffect(() => {
    if (open) setDraft(selected);
  }, [open, selected]);

  useEffect(() => {
    if (!open) return;
    function onPointer(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function toggle(groupId: string, optionId: string) {
    const current = draft[groupId] ?? [];
    const next = current.includes(optionId)
      ? current.filter((id) => id !== optionId)
      : [...current, optionId];
    setDraft({ ...draft, [groupId]: next });
  }

  return (
    <div className="popover" ref={rootRef}>
      <button
        type="button"
        className="icon-btn"
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-labelledby={labelId}
        onClick={() => setOpen((value) => !value)}
      >
        <FilterIcon />
        <span id={labelId} className="sr-only">
          Filters
        </span>
        {activeCount > 0 && <span className="count-badge">{activeCount}</span>}
      </button>
      {open && (
        <div className="popover-panel" role="dialog" aria-label="Filters">
          <div className="popover-body">
            {groups.map((group) => (
              <fieldset key={group.id} className="filter-group">
                <legend>{group.label}</legend>
                <div className="filter-options">
                  {group.options.map((option) => (
                    <label key={option.id} className="filter-option">
                      <input
                        type="checkbox"
                        checked={(draft[group.id] ?? []).includes(option.id)}
                        onChange={() => toggle(group.id, option.id)}
                      />
                      {option.tone ? (
                        <StatusBadge status={option.tone} />
                      ) : (
                        <span>{option.label}</span>
                      )}
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
          </div>
          <div className="popover-actions">
            <button
              type="button"
              className="secondary-btn"
              onClick={() => {
                const emptied = Object.fromEntries(
                  groups.map((group) => [group.id, [] as string[]]),
                );
                setDraft(emptied);
                onClear();
                setOpen(false);
              }}
            >
              Clear
            </button>
            <button
              type="button"
              className="primary-btn"
              onClick={() => {
                onApply(draft);
                setOpen(false);
              }}
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function FilterIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path
        d="M2 3h12L9.5 9v4l-3 1.5V9L2 3z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}
