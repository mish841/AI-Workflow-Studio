import type { ReactNode } from "react";
import type { View, WorkspaceId } from "../types";
import { WORKSPACE_TITLES } from "../lib/assessment";

const NAV: { id: View; label: string; securityOnly?: boolean }[] = [
  { id: "workspaces", label: "Workspaces" },
  { id: "documents", label: "Documents" },
  { id: "assessments", label: "Assessments" },
  { id: "findings", label: "Findings" },
  { id: "compare", label: "Compare", securityOnly: true },
];

const WORKSPACE_NOTE: Record<WorkspaceId, string> = {
  security:
    "Assessments evaluate the selected document against Northstar security requirements.",
  sox: "Assessments run ITGC checks on synthetic period evidence. Not a SOX opinion.",
  project_qa: "Assessments run PMO checks on portal-program artifacts.",
  content: "Assessments run a short style-guide rule set on one announcement.",
};

type Props = {
  view: View;
  workspace: WorkspaceId;
  onNavigate: (view: View) => void;
  children: ReactNode;
};

export function AppShell({ view, workspace, onNavigate, children }: Props) {
  const items = NAV.filter((item) => !item.securityOnly || workspace === "security");
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <p className="brand-kicker">AI Workflow Studio</p>
          <h1>Quality Review</h1>
          <p className="brand-org">Northstar Technologies</p>
          <span className="demo-pill">Synthetic Dataset Demo</span>
        </div>
        <nav aria-label="Primary">
          {items.map((item) => (
            <button
              key={item.id}
              className={view === item.id ? "nav-btn active" : "nav-btn"}
              onClick={() => onNavigate(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <p className="sidebar-note">
          Active workspace: {WORKSPACE_TITLES[workspace]}. {WORKSPACE_NOTE[workspace]}
        </p>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <div>
            <strong>Northstar Technologies</strong>
            <span className="topbar-sep">·</span>
            <span>{WORKSPACE_TITLES[workspace]}</span>
          </div>
          <span className="demo-pill">Northstar Demo</span>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
