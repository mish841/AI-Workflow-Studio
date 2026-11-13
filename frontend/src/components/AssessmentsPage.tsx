import type {
  AssessmentRun,
  ComplianceStatus,
  DatasetDocument,
  PolicyVersion,
} from "../types";
import { dataset, STATUS_LABELS } from "../lib/dataset";
import { sourceLabel } from "../lib/assessment";
import { AssessmentDetails } from "./AssessmentDetails";
import { PolicyPicker } from "./PolicyPicker";
import { StatusBadge } from "./StatusBadge";

type Props = {
  policies: DatasetDocument[];
  selectedPolicy: PolicyVersion;
  onSelectPolicy: (version: PolicyVersion) => void;
  isRunning: boolean;
  error: string | null;
  run: AssessmentRun | null;
  onRunLive: () => void;
  onLoadSample: () => void;
  onViewFindings: () => void;
};

const STATUSES: ComplianceStatus[] = [
  "satisfied",
  "partial",
  "missing",
  "contradicted",
];

export function AssessmentsPage({
  policies,
  selectedPolicy,
  onSelectPolicy,
  isRunning,
  error,
  run,
  onRunLive,
  onLoadSample,
  onViewFindings,
}: Props) {
  const standards = dataset.documents.filter((doc) => doc.kind === "standard");
  const requirementCount = dataset.requirements.length;
  const selectedTitle =
    policies.find((doc) => doc.policyVersion === selectedPolicy)?.title ??
    "Selected document";

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
          <PolicyPicker
            policies={policies}
            selected={selectedPolicy}
            onSelect={onSelectPolicy}
            disabled={isRunning}
            labelledBy="Select document"
            searchLabel="Search documents"
          />
        </div>

        <div className="workflow-step">
          <p className="eyebrow">2. Review against</p>
          <p>
            {requirementCount} requirements from {standards.length} reference
            standards.
          </p>
          <ul className="standard-list">
            {standards.map((standard) => (
              <li key={standard.id}>{standard.title}</li>
            ))}
          </ul>
        </div>

        <div className="workflow-step">
          <p className="eyebrow">3. Run assessment</p>
          <p className="muted">
            Assess {selectedTitle} against the reference requirements. Findings
            will show whether each requirement is satisfied, partial, missing, or
            contradicted, with source verification on quoted evidence.
          </p>
          <div className="assess-actions">
            <button
              type="button"
              className="primary-btn"
              onClick={onRunLive}
              disabled={isRunning}
            >
              {isRunning ? "Assessing…" : "Run assessment"}
            </button>
            <button
              type="button"
              className="secondary-btn"
              onClick={onLoadSample}
              disabled={isRunning}
            >
              View sample results
            </button>
          </div>
          <p className="muted">
            Sample results are pre-labeled reference findings for this synthetic
            dataset. They are not a live AI assessment.
          </p>
        </div>

        {isRunning && (
          <div className="loading-panel" role="status">
            <span className="spinner" aria-hidden="true" />
            <p>
              Reviewing the selected document against the reference requirements.
              This can take a few minutes.
            </p>
          </div>
        )}
        {error && (
          <p className="error-banner" role="alert">
            {error}
          </p>
        )}
      </section>

      {!run && !isRunning && !error && (
        <p className="muted">
          Choose a document, confirm the standards, then run the assessment.
        </p>
      )}

      {run && !isRunning && (
        <section className="card compact-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">Assessment complete</p>
              <h3>{run.title}</h3>
              <p className="meta-line">
                {sourceLabel(run.kind)}
                {" · "}
                {run.summary.total} requirements evaluated
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
          <dl className="live-stats">
            <div>
              <dt>Needs review</dt>
              <dd>{run.summary.needsReview}</dd>
            </div>
            <div>
              <dt>Source verified</dt>
              <dd>{run.summary.verifiedQuotes}</dd>
            </div>
            <div>
              <dt>Could not complete</dt>
              <dd>{run.summary.failed}</dd>
            </div>
          </dl>
          <div className="bar" aria-label="Compliance distribution">
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
