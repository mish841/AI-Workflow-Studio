import { useState, type ReactNode } from "react";
import type { WorkspaceId } from "../types";
import { Chevron } from "./Chevron";

type Props = {
  onOpen: (workspace: WorkspaceId) => void;
};

export function WorkspacesPage({ onOpen }: Props) {
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Northstar Technologies</p>
          <h2>Workspaces</h2>
        </div>
      </div>

      <div className="workspace-grid">
        <WorkspaceCard
          status="Available"
          title="Security & Compliance"
          summary="Assess security policies against Northstar reference requirements."
          actionLabel="Open workspace"
          onAction={() => onOpen("security")}
          primary
          details={
            <>
              <p>
                Working demo uses Information Security Policy V1 and V2 against
                18 reference requirements.
              </p>
              <p>
                Run a document assessment, inspect findings, and compare policy
                versions.
              </p>
            </>
          }
        />
        <WorkspaceCard
          status="Available"
          title="SOX / IT Controls"
          summary="Review synthetic IT general controls and period evidence."
          actionLabel="Open workspace"
          onAction={() => onOpen("sox")}
          details={
            <>
              <p>Eleven fictional ITGCs covering access, change, SoD, and evidence.</p>
              <p>
                Deterministic checks distinguish control design, evidence
                completeness, and operating effectiveness. This is not a SOX
                audit opinion.
              </p>
            </>
          }
        />
        <WorkspaceCard
          status="Available"
          title="Project Quality Assurance"
          summary="Audit delivery artifacts such as plans, RAID logs, and status reports."
          actionLabel="Open workspace"
          onAction={() => onOpen("project_qa")}
          details={
            <>
              <p>
                Charter, plan, RAID log, decision log, and status report for a
                fictional portal program.
              </p>
              <p>Excel/Gantt review is not built.</p>
            </>
          }
        />
        <WorkspaceCard
          status="Available"
          title="Content Quality & Standards"
          summary="Review communications against writing and style standards."
          actionLabel="Open workspace"
          onAction={() => onOpen("content")}
          details={
            <p>
              A short style guide and one announcement, with checks for metadata,
              required sections, and prohibited terms.
            </p>
          }
        />
      </div>
    </div>
  );
}

function WorkspaceCard({
  status,
  title,
  summary,
  actionLabel,
  onAction,
  details,
  primary,
}: {
  status: string;
  title: string;
  summary: string;
  actionLabel: string;
  onAction: () => void;
  details: ReactNode;
  primary?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <article className={primary ? "workspace-card" : "workspace-card"}>
      <p className="eyebrow">{status}</p>
      <h3>{title}</h3>
      <p>{summary}</p>
      <div className="card-actions">
        <button
          type="button"
          className={primary ? "primary-btn" : "secondary-btn"}
          onClick={onAction}
        >
          {actionLabel}
        </button>
        <button
          type="button"
          className="text-btn"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          Details <Chevron open={open} />
        </button>
      </div>
      {open && <div className="card-details">{details}</div>}
    </article>
  );
}
