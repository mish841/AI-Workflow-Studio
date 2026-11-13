import { useState } from "react";
import type { AssessmentRun } from "../types";
import { formatDuration, methodLabel, sourceLabel } from "../lib/assessment";
import { Chevron } from "./Chevron";

export function AssessmentDetails({ run }: { run: AssessmentRun }) {
  const [open, setOpen] = useState(false);
  const retrieval =
    run.retrievalReady == null
      ? "Not recorded"
      : run.retrievalReady
        ? "Source library ready"
        : "Source library not ready";
  const requested =
    run.requestedMode === "auto"
      ? "Automatic"
      : run.requestedMode
        ? methodLabel(run.requestedMode)
        : "Not recorded";

  return (
    <div className="assessment-details">
      <button
        type="button"
        className="group-toggle"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <Chevron open={open} />
        Assessment details
      </button>
      {open ? (
        <dl className="details-dl">
          <div>
            <dt>Result type</dt>
            <dd>{sourceLabel(run.kind)}</dd>
          </div>
          <div>
            <dt>Evaluation method</dt>
            <dd>
              {methodLabel(run.evaluationMode)}
              {run.evaluationMode !== "deterministic"
                ? ` (${run.evaluationMode})`
                : ""}
            </dd>
          </div>
          <div>
            <dt>Requested</dt>
            <dd>{requested}</dd>
          </div>
          <div>
            <dt>Fallback</dt>
            <dd>
              {run.fallbackUsed
                ? "Yes — full document used because source passages were not ready"
                : "No"}
            </dd>
          </div>
          <div>
            <dt>Retrieval status</dt>
            <dd>{retrieval}</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>
              {run.kind === "deterministic"
                ? "Structured rules (no language model)"
                : (run.model ?? "Not recorded")}
            </dd>
          </div>
          <div>
            <dt>Processing time</dt>
            <dd>{formatDuration(run.durationMs)}</dd>
          </div>
          {run.evaluationId ? (
            <div>
              <dt>Assessment ID</dt>
              <dd>{run.evaluationId}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}
    </div>
  );
}
