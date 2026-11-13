import type { DocumentKind, WorkspaceId } from "../types";

export const REVIEW_WORKSPACES: Exclude<WorkspaceId, "security">[] = [
  "sox",
  "project_qa",
  "content",
];

export const DOCUMENT_GROUPS: Record<
  WorkspaceId,
  { kind: DocumentKind; title: string }[]
> = {
  security: [
    { kind: "standard", title: "Reference standards" },
    { kind: "policy", title: "Company policies" },
  ],
  sox: [
    { kind: "control", title: "Control catalog" },
    { kind: "evidence", title: "Period evidence" },
  ],
  project_qa: [{ kind: "artifact", title: "Project artifacts" }],
  content: [
    { kind: "guide", title: "Style guide" },
    { kind: "sample", title: "Sample documents" },
  ],
};

export const WORKSPACE_REVIEW_COPY: Record<
  Exclude<WorkspaceId, "security">,
  { summary: string; disclaimer: string }
> = {
  sox: {
    summary:
      "Run ITGC checks on the Q3 2026 Northstar evidence package.",
    disclaimer:
      "This is a synthetic controls review. It is not a SOX audit opinion and does not assess a real company.",
  },
  project_qa: {
    summary:
      "Check the Customer Portal Refresh artifacts for missing owners, dates, sections, and metadata drift.",
    disclaimer:
      "Deterministic PMO checks only. Excel, Microsoft Project, and critical-path analysis are not implemented.",
  },
  content: {
    summary:
      "Check the portal login announcement against the internal writing standard.",
    disclaimer:
      "A limited rule review for metadata, required sections, and prohibited terms.",
  },
};
