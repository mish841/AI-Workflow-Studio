import { useMemo, useState, type ReactNode } from "react";
import type { DatasetDocument, DocumentKind } from "../types";
import { Chevron } from "./Chevron";
import { FilterPopover } from "./FilterPopover";

const DEFAULT_GROUPS: { kind: DocumentKind; title: string }[] = [
  { kind: "standard", title: "Reference standards" },
  { kind: "policy", title: "Company policies" },
];

type Props = {
  documents: DatasetDocument[];
  groups?: { kind: DocumentKind; title: string }[];
};

function sectionsOf(content: string): { label: string; index: number }[] {
  return content
    .split("\n")
    .map((line, index) => ({ line, index }))
    .filter(({ line }) => /^\d+\.\s+\S/.test(line.trim()))
    .map(({ line, index }) => ({ label: line.trim(), index }));
}

export function DocumentsPage({ documents, groups = DEFAULT_GROUPS }: Props) {
  const [selectedId, setSelectedId] = useState(documents[0]?.id ?? "");
  const [listQuery, setListQuery] = useState("");
  const [kinds, setKinds] = useState<DocumentKind[]>([]);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(groups.map((group) => [group.kind, true])),
  );
  const [docQuery, setDocQuery] = useState("");

  const selected = useMemo(
    () => documents.find((doc) => doc.id === selectedId) ?? documents[0],
    [documents, selectedId],
  );

  const visible = useMemo(() => {
    const needle = listQuery.trim().toLowerCase();
    return documents.filter((doc) => {
      if (kinds.length && !kinds.includes(doc.kind)) return false;
      if (!needle) return true;
      return (
        doc.title.toLowerCase().includes(needle) ||
        doc.file.toLowerCase().includes(needle)
      );
    });
  }, [documents, kinds, listQuery]);

  const grouped = groups.map((group) => ({
    ...group,
    docs: visible.filter((doc) => doc.kind === group.kind),
  }));
  const sections = selected ? sectionsOf(selected.content) : [];
  const needle = docQuery.trim().toLowerCase();
  const matchCount =
    selected && needle
      ? selected.content.toLowerCase().split(needle).length - 1
      : 0;

  function select(id: string) {
    const doc = documents.find((item) => item.id === id);
    setSelectedId(id);
    setDocQuery("");
    if (doc) {
      setOpenGroups((current) => ({ ...current, [doc.kind]: true }));
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Library</p>
          <h2>Documents</h2>
        </div>
      </div>

      <div className="split library-split">
        <div className="doc-list">
          <div className="list-toolbar">
            <input
              type="search"
              placeholder="Search documents"
              value={listQuery}
              onChange={(event) => setListQuery(event.target.value)}
            />
            <FilterPopover
              groups={[
                {
                  id: "kind",
                  label: "Type",
                  options: groups.map((group) => ({
                    id: group.kind,
                    label: group.title,
                  })),
                },
              ]}
              selected={{ kind: kinds }}
              activeCount={kinds.length}
              onApply={(next) => setKinds((next.kind ?? []) as DocumentKind[])}
              onClear={() => setKinds([])}
            />
          </div>

          <div className="doc-scroll">
          {grouped.map((group) => (
            <CollapsibleList
              key={group.kind}
              title={group.title}
              open={openGroups[group.kind] ?? true}
              onToggle={() =>
                setOpenGroups((current) => ({
                  ...current,
                  [group.kind]: !(current[group.kind] ?? true),
                }))
              }
            >
              {group.docs.map((doc) => (
                <DocButton
                  key={doc.id}
                  doc={doc}
                  active={selected?.id === doc.id}
                  onSelect={select}
                />
              ))}
              {group.docs.length === 0 && <p className="empty">No matches.</p>}
            </CollapsibleList>
          ))}
          </div>
        </div>

        <article className="reader">
          {selected ? (
            <>
              <div className="reader-header">
                <div>
                  <p className="eyebrow">
                    {groups.find((group) => group.kind === selected.kind)?.title ??
                      selected.kind}
                  </p>
                  <h3>{selected.title}</h3>
                  <p className="meta-line">
                    {selected.file}
                    {selected.policyVersion
                      ? ` · ${selected.policyVersion.toUpperCase()}`
                      : ""}
                  </p>
                </div>
              </div>

              <div className="reader-tools">
                <input
                  type="search"
                  placeholder="Search in document"
                  value={docQuery}
                  onChange={(event) => setDocQuery(event.target.value)}
                />
                {needle ? (
                  <span className="muted">
                    {matchCount} match{matchCount === 1 ? "" : "es"}
                  </span>
                ) : null}
              </div>

              {sections.length > 0 && (
                <nav className="section-nav" aria-label="Sections">
                  {sections.map((section) => (
                    <a key={section.index} href={`#doc-line-${section.index}`}>
                      {section.label}
                    </a>
                  ))}
                </nav>
              )}

              <div className="document-body">
                {selected.content.split("\n").map((line, index) => (
                  <p key={index} id={`doc-line-${index}`}>
                    {highlight(line, needle)}
                  </p>
                ))}
              </div>
            </>
          ) : (
            <p className="empty">No documents are available.</p>
          )}
        </article>
      </div>
    </div>
  );
}

function CollapsibleList({
  title,
  open,
  onToggle,
  children,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <section>
      <button
        type="button"
        className="group-toggle"
        aria-expanded={open}
        onClick={onToggle}
      >
        <Chevron open={open} />
        {title}
      </button>
      {open && <div>{children}</div>}
    </section>
  );
}

function DocButton({
  doc,
  active,
  onSelect,
}: {
  doc: DatasetDocument;
  active: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      className={active ? "doc-item active" : "doc-item"}
      onClick={() => onSelect(doc.id)}
    >
      <span>{doc.title}</span>
      <small>{doc.file}</small>
    </button>
  );
}

function highlight(line: string, needle: string) {
  if (!needle) return line;
  const lower = line.toLowerCase();
  const parts: Array<string | { mark: string }> = [];
  let cursor = 0;
  while (cursor < line.length) {
    const found = lower.indexOf(needle, cursor);
    if (found === -1) {
      parts.push(line.slice(cursor));
      break;
    }
    if (found > cursor) parts.push(line.slice(cursor, found));
    parts.push({ mark: line.slice(found, found + needle.length) });
    cursor = found + needle.length;
  }
  return parts.map((part, index) =>
    typeof part === "string" ? (
      part
    ) : (
      <mark key={index}>{part.mark}</mark>
    ),
  );
}
