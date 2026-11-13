import type { AssessmentRun, ComplianceStatus } from "../types";
import { STATUS_LABELS } from "../lib/dataset";
import { sourceLabel } from "../lib/assessment";
import { AssessmentDetails } from "./AssessmentDetails";
import { StatusBadge } from "./StatusBadge";

type Props = {
  title: string;
  disclaimer: string;
  summary: string;
  isRunning: boolean;
  error: string | null;
  run: AssessmentRun | null;
  onRun: () => void;
  onViewFindings: () => void;
};

const STATUSES: ComplianceStatus[] = [
  "satisfied",
  "partial",
  "missing",
  "contradicted",
];

export function WorkspaceReviewPage({
  title,
  disclaimer,
  summary,
  isRunning,
  error,
  run,
  onRun,
  onViewFindings,
}: Props) {
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Workflow</p>
          <h2>Assessment</h2>
        </div>
      </div>

      <section className="card compact-card">
        <div className="workflow-step">
          <p className="eyebrow">1. Select document</p>
          <h3>{title}</h3>
          <p className="muted">
            This workspace uses the prepared artifact package for {title}.
          </p>
        </div>

        <div className="workflow-step">
          <p className="eyebrow">2. Review against</p>
          <p>{summary}</p>
          <p className="banner">{disclaimer}</p>
        </div>

        <div className="workflow-step">
          <p className="eyebrow">3. Run assessment</p>
          <div className="assess-actions">
            <button
              type="button"
              className="primary-btn"
              onClick={onRun}
              disabled={isRunning}
            >
              {isRunning ? "Assessing…" : "Run assessment"}
            </button>
          </div>
        </div>

        {isRunning && (
          <div className="loading-panel" role="status">
            <span className="spinner" aria-hidden="true" />
            <p>Checking the workspace artifacts against the defined rules.</p>
          </div>
        )}
        {error && (
          <p className="error-banner" role="alert">
            {error}
          </p>
        )}
      </section>

      {run && !isRunning && (
        <section className="card compact-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">Assessment complete</p>
              <h3>{run.title}</h3>
              <p className="meta-line">
                {sourceLabel(run.kind)} · {run.summary.total} checks
              </p>
            </div>
            <button type="button" className="secondary-btn" onClick={onViewFindings}>
              Review findings
            </button>
          </div>
          <div className="summary-grid compact-summary">
            {STATUSES.map((status) => (
              <article key={status} className="summary-card">
                <StatusBadge status={status} />
                <strong>{run.summary.statusCounts[status]}</strong>
              </article>
            ))}
          </div>
          <div className="bar" aria-label="Finding distribution">
            {STATUSES.map((status) => {
              const denom = Object.values(run.summary.statusCounts).reduce(
                (sum, value) => sum + value,
                0,
              );
              const width = denom === 0 ? 0 : (run.summary.statusCounts[status] / denom) * 100;
              return (
                <div
                  key={status}
                  className={`bar-seg tone-${status}`}
                  style={{ width: `${width}%` }}
                  title={`${STATUS_LABELS[status]}: ${run.summary.statusCounts[status]}`}
                />
              );
            })}
          </div>
          <AssessmentDetails run={run} />
        </section>
      )}
    </div>
  );
}
