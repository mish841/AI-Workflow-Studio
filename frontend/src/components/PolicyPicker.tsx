import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { DatasetDocument, PolicyVersion } from "../types";
import { Chevron } from "./Chevron";
import { FilterPopover } from "./FilterPopover";

type Props = {
  policies: DatasetDocument[];
  selected: PolicyVersion;
  onSelect: (version: PolicyVersion) => void;
  disabled?: boolean;
  compact?: boolean;
  heading?: string;
  labelledBy?: string;
  searchLabel?: string;
};

export function PolicyPicker({
  policies,
  selected,
  onSelect,
  disabled,
  compact,
  heading,
  labelledBy,
  searchLabel = "Search policies",
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [versions, setVersions] = useState<string[]>([]);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();

  const selectedDoc =
    policies.find((doc) => doc.policyVersion === selected) ?? policies[0];
  const selectedTitle = selectedDoc?.title ?? "";

  const versionOptions = useMemo(() => {
    const ids = [
      ...new Set(
        policies
          .map((doc) => doc.policyVersion)
          .filter((value): value is PolicyVersion => Boolean(value)),
      ),
    ];
    return ids.map((id) => ({
      id,
      label: id.toUpperCase(),
    }));
  }, [policies]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const browsingSelected = !needle || needle === selectedTitle.toLowerCase();
    return policies.filter((doc) => {
      if (!doc.policyVersion) return false;
      if (versions.length && !versions.includes(doc.policyVersion)) return false;
      if (browsingSelected) return true;
      return (
        doc.title.toLowerCase().includes(needle) ||
        doc.file.toLowerCase().includes(needle)
      );
    });
  }, [policies, query, selectedTitle, versions]);

  useEffect(() => {
    if (!open) return;
    function onPointer(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) closeList();
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") closeList();
    }
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function closeList() {
    setOpen(false);
    setQuery("");
  }

  function openList() {
    if (disabled) return;
    setQuery(selectedTitle);
    setOpen(true);
    window.requestAnimationFrame(() => {
      inputRef.current?.select();
    });
  }

  function selectPolicy(version: PolicyVersion) {
    onSelect(version);
    setQuery("");
    setOpen(false);
  }

  const fieldValue = open ? query : selectedTitle;
  const itemNoun = searchLabel.toLowerCase().includes("document")
    ? "documents"
    : "policies";

  return (
    <div
      className={compact ? "policy-picker compact" : "policy-picker"}
      ref={rootRef}
    >
      {heading ? <p className="eyebrow">{heading}</p> : null}
      <div className="list-toolbar">
        <div className={open ? "policy-combobox is-open" : "policy-combobox"}>
          <input
            ref={inputRef}
            id={listId + "-input"}
            type="text"
            role="combobox"
            aria-expanded={open}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-label={labelledBy ?? searchLabel}
            placeholder={searchLabel}
            value={fieldValue}
            onChange={(event) => {
              setQuery(event.target.value);
              setOpen(true);
            }}
            onFocus={() => {
              if (!open) openList();
            }}
            disabled={disabled}
            className="policy-combobox-field"
          />
          <button
            type="button"
            className="policy-combobox-toggle"
            aria-label={open ? `Hide ${itemNoun}` : `Show ${itemNoun}`}
            aria-expanded={open}
            aria-controls={listId}
            disabled={disabled}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => {
              if (open) closeList();
              else openList();
            }}
          >
            <Chevron open={open} />
          </button>
        </div>
        <FilterPopover
          groups={[
            {
              id: "version",
              label: "Version",
              options: versionOptions,
            },
          ]}
          selected={{ version: versions }}
          activeCount={versions.length}
          onApply={(next) => setVersions(next.version ?? [])}
          onClear={() => setVersions([])}
        />
      </div>

      {selectedDoc?.policyVersion && !compact && !open ? (
        <p className="meta-line">
          Selected: {selectedDoc.title} · {selectedDoc.file}
        </p>
      ) : null}

      {open ? (
        <div
          className="policy-picker-list"
          id={listId}
          role="listbox"
          aria-label={labelledBy ?? "Company policies"}
        >
          {visible.length === 0 ? (
            <p className="empty">No policies match the current search or filters.</p>
          ) : (
            visible.map((doc) => {
              const version = doc.policyVersion;
              if (!version) return null;
              const active = selected === version;
              return (
                <button
                  key={doc.id}
                  type="button"
                  role="option"
                  aria-selected={active}
                  className={active ? "policy-row active" : "policy-row"}
                  disabled={disabled}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => selectPolicy(version)}
                >
                  <span className="policy-row-title">{doc.title}</span>
                  <span className="policy-row-meta">
                    {doc.file}
                    <span className="policy-version-chip">{version.toUpperCase()}</span>
                  </span>
                </button>
              );
            })
          )}
        </div>
      ) : null}
    </div>
  );
}
