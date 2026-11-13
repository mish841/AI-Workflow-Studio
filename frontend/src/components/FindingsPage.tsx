import { useMemo, useState } from "react";
import type { AssessmentRun, DisplayStatus } from "../types";
import { DISPLAY_STATUS_LABELS, sourceLabel } from "../lib/assessment";
import { FilterPopover } from "./FilterPopover";
import { FindingDetail } from "./FindingDetail";
import { StatusBadge } from "./StatusBadge";

type Props = {
  run: AssessmentRun | null;
  onGoAssess: () => void;
};

const FILTER_STATUSES: DisplayStatus[] = [
  "satisfied",
  "partial",
  "missing",
  "contradicted",
  "needs_review",
  "failed",
];

export function FindingsPage({ run, onGoAssess }: Props) {
  const [query, setQuery] = useState("");
  const [statuses, setStatuses] = useState<DisplayStatus[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [dimensions, setDimensions] = useState<string[]>([]);
  const [pinned, setPinned] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(
    run?.findings[0]?.id ?? null,
  );

  const categoryOptions = useMemo(() => {
    const labels = [...new Set((run?.findings ?? []).map((item) => item.categoryLabel))];
    return labels.map((label) => ({ id: label, label }));
  }, [run]);

  const dimensionOptions = useMemo(() => {
    const labels = [
      ...new Set(
        (run?.findings ?? [])
          .map((item) => item.dimensionLabel)
          .filter((value): value is string => Boolean(value)),
      ),
    ];
    return labels.map((label) => ({ id: label, label }));
  }, [run]);

  const rows = useMemo(() => {
    if (!run) return [];
    const needle = query.trim().toLowerCase();
    return run.findings.filter((finding) => {
      if (statuses.length && !statuses.includes(finding.displayStatus)) return false;
      if (categories.length && !categories.includes(finding.categoryLabel)) {
        return false;
      }
      if (
        dimensions.length &&
        (!finding.dimensionLabel || !dimensions.includes(finding.dimensionLabel))
      ) {
        return false;
      }
      if (!needle) return true;
      return (
        finding.id.toLowerCase().includes(needle) ||
        finding.title.toLowerCase().includes(needle) ||
        finding.categoryLabel.toLowerCase().includes(needle)
      );
    });
  }, [categories, dimensions, query, run, statuses]);

  const selected = rows.find((row) => row.id === selectedId) ?? rows[0] ?? null;
  const activeCount = statuses.length + categories.length + dimensions.length;

  if (!run) {
    return (
      <div className="page">
        <div className="empty-card">
          <h2>No findings yet</h2>
          <p>Run an assessment to populate this table.</p>
          <button type="button" className="primary-btn" onClick={onGoAssess}>
            Go to Assessments
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={pinned ? "page page-pinned-detail" : "page"}>
      <div className="page-header">
        <div>
          <p className="eyebrow">{sourceLabel(run.kind)}</p>
          <h2>Findings · {run.title}</h2>
        </div>
        {run.evaluationId ? (
          <p className="meta-line">Evaluation {run.evaluationId}</p>
        ) : null}
      </div>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search findings"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <FilterPopover
          groups={[
            {
              id: "status",
              label: "Status",
              options: FILTER_STATUSES.map((status) => ({
                id: status,
                label: DISPLAY_STATUS_LABELS[status],
                tone: status,
              })),
            },
            { id: "category", label: "Category", options: categoryOptions },
            ...(dimensionOptions.length
              ? [{ id: "dimension", label: "Dimension", options: dimensionOptions }]
              : []),
          ]}
          selected={{
            status: statuses,
            category: categories,
            dimension: dimensions,
          }}
          activeCount={activeCount}
          onApply={(next) => {
            setStatuses((next.status ?? []) as DisplayStatus[]);
            setCategories(next.category ?? []);
            setDimensions(next.dimension ?? []);
          }}
          onClear={() => {
            setStatuses([]);
            setCategories([]);
            setDimensions([]);
          }}
        />
      </div>

      <div className={pinned ? "split findings-split detail-pinned" : "split findings-split"}>
        <div className="table-wrap">
          {rows.length === 0 ? (
            <p className="empty">No findings match the current search or filters.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>{run.kind === "deterministic" ? "Check" : "Requirement"}</th>
                  <th>Category</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((finding) => (
                  <tr
                    key={finding.id}
                    className={selected?.id === finding.id ? "selected" : undefined}
                    tabIndex={0}
                    onClick={() => setSelectedId(finding.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedId(finding.id);
                      }
                    }}
                  >
                    <td>{finding.id}</td>
                    <td>{finding.title}</td>
                    <td>{finding.categoryLabel}</td>
                    <td>
                      <StatusBadge status={finding.displayStatus} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <FindingDetail
          finding={selected}
          kind={run.kind}
          version={run.policyVersion}
          pinned={pinned}
          onTogglePin={() => setPinned((value) => !value)}
        />
      </div>
    </div>
  );
}
