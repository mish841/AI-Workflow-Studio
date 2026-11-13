import type {
  AssessmentKind,
  AssessmentRun,
  AssessmentSummary,
  ComplianceStatus,
  DisplayStatus,
  EvaluationApiResult,
  FindingView,
  PolicyVersion,
  Requirement,
  ReviewApiResult,
  ReviewDimension,
  StatusCounts,
  WorkspaceId,
} from "../types";
const POLICY_LABELS: Record<PolicyVersion, string> = {
  v1: "Security Policy V1",
  v2: "Security Policy V2",
};
const POLICY_FILES: Record<PolicyVersion, string> = {
  v1: "security_policy_v1.txt",
  v2: "security_policy_v2.txt",
};

export const CATEGORY_LABELS: Record<string, string> = {
  access_control: "Access Control",
  authentication: "Authentication",
  data_protection: "Data Protection",
  incident_response: "Incident Response",
};

export const DIMENSION_LABELS: Record<ReviewDimension, string> = {
  design: "Control design",
  completeness: "Evidence completeness",
  operating_effectiveness: "Operating effectiveness",
  artifact_quality: "Artifact quality",
  style: "Style rule",
};

export const WORKSPACE_TITLES: Record<WorkspaceId, string> = {
  security: "Security & Compliance",
  sox: "SOX / IT Controls",
  project_qa: "Project Quality Assurance",
  content: "Content Quality & Standards",
};

export const DISPLAY_STATUS_LABELS: Record<DisplayStatus, string> = {
  satisfied: "Satisfied",
  partial: "Partial",
  missing: "Missing",
  contradicted: "Contradicted",
  needs_review: "Needs review",
  failed: "Evaluation failed",
};

const EMPTY_COUNTS: StatusCounts = {
  satisfied: 0,
  partial: 0,
  missing: 0,
  contradicted: 0,
};

export function categoryLabel(category: string, fallback?: string): string {
  return CATEGORY_LABELS[category] ?? fallback ?? category;
}

export function displayStatusFor(finding: {
  classification: ComplianceStatus | null;
  evaluationState: FindingView["evaluationState"];
  needsReview: boolean;
}): DisplayStatus {
  if (finding.evaluationState === "failed") return "failed";
  if (finding.evaluationState === "needs_review" || finding.needsReview) {
    return "needs_review";
  }
  if (finding.classification) return finding.classification;
  return "needs_review";
}

export function summarizeFindings(findings: FindingView[]): AssessmentSummary {
  const statusCounts: StatusCounts = { ...EMPTY_COUNTS };
  let needsReview = 0;
  let failed = 0;
  let verifiedQuotes = 0;
  for (const finding of findings) {
    if (finding.evaluationState === "failed") failed += 1;
    if (finding.needsReview || finding.evaluationState === "needs_review") {
      needsReview += 1;
    }
    if (finding.evidenceVerified) verifiedQuotes += 1;
    if (finding.evaluationState === "completed" && finding.classification) {
      statusCounts[finding.classification] += 1;
    }
  }
  return {
    total: findings.length,
    statusCounts,
    needsReview,
    failed,
    verifiedQuotes,
  };
}

export function mapLiveResult(result: EvaluationApiResult): AssessmentRun {
  const findings = result.findings.map((item) => {
    const mapped: FindingView = {
      id: item.requirement_id,
      title: item.requirement_title,
      category: item.category,
      categoryLabel: categoryLabel(item.category),
      fullText: item.requirement_text,
      classification: item.classification,
      displayStatus: displayStatusFor({
        classification: item.classification,
        evaluationState: item.evaluation_state,
        needsReview: item.needs_review,
      }),
      explanation: item.explanation,
      evidence: item.supporting_quote,
      evidenceVerified: item.evidence_verified,
      evidenceVerification: item.evidence_verification,
      sourceDocument: item.source_document,
      needsReview: item.needs_review,
      evaluationState: item.evaluation_state,
      uncertaintyNote: item.uncertainty_note,
      retrievedPassages: item.retrieved_passages ?? [],
      dimension: null,
      dimensionLabel: null,
    };
    return mapped;
  });
  return {
    kind: "live",
    workspace: "security",
    title: POLICY_LABELS[result.policy_version],
    policyVersion: result.policy_version,
    evaluationId: result.id,
    sourceDocument: result.source_document,
    evaluationMode: result.evaluation_mode ?? "direct",
    requestedMode: result.requested_mode ?? result.evaluation_mode ?? "direct",
    fallbackUsed: Boolean(result.fallback_used),
    retrievalReady: result.retrieval_ready ?? null,
    model: result.model ?? "gpt-4o-mini",
    durationMs: result.duration_ms ?? null,
    findings,
    summary: summarizeFindings(findings),
  };
}

export function mapSampleResult(
  requirements: Requirement[],
  version: PolicyVersion,
): AssessmentRun {
  const findings = requirements.map((requirement) => {
    const labeled = requirement.findings[version];
    const mapped: FindingView = {
      id: requirement.id,
      title: requirement.title,
      category: requirement.category,
      categoryLabel: requirement.categoryLabel,
      fullText: requirement.fullText,
      classification: labeled.status,
      displayStatus: labeled.status,
      explanation: labeled.reason,
      evidence: labeled.evidence,
      evidenceVerified: Boolean(labeled.evidence),
      evidenceVerification: labeled.evidence ? "verified" : "missing",
      sourceDocument: requirement.sourceFile,
      needsReview: false,
      evaluationState: "completed",
      uncertaintyNote: null,
      retrievedPassages: [],
      dimension: null,
      dimensionLabel: null,
    };
    return mapped;
  });
  return {
    kind: "sample",
    workspace: "security",
    title: POLICY_LABELS[version],
    policyVersion: version,
    evaluationId: null,
    sourceDocument: POLICY_FILES[version],
    evaluationMode: "direct",
    findings,
    summary: summarizeFindings(findings),
  };
}

export function mapReviewResult(result: ReviewApiResult): AssessmentRun {
  const findings = result.findings.map((item) => {
    const mapped: FindingView = {
      id: item.id,
      title: item.title,
      category: item.category,
      categoryLabel: categoryLabel(item.category, item.category.replace(/_/g, " ")),
      fullText: item.full_text,
      classification: item.classification,
      displayStatus: displayStatusFor({
        classification: item.classification,
        evaluationState: item.evaluation_state,
        needsReview: item.needs_review,
      }),
      explanation: item.explanation,
      evidence: item.evidence,
      evidenceVerified: item.evidence_verified,
      evidenceVerification: item.evidence ? "verified" : "missing",
      sourceDocument: item.source_document,
      needsReview: item.needs_review,
      evaluationState: item.evaluation_state,
      uncertaintyNote: null,
      retrievedPassages: [],
      dimension: item.dimension,
      dimensionLabel: DIMENSION_LABELS[item.dimension],
    };
    return mapped;
  });
  return {
    kind: "deterministic",
    workspace: result.workspace,
    title: WORKSPACE_TITLES[result.workspace],
    policyVersion: null,
    evaluationId: result.id,
    sourceDocument: result.source_document,
    evaluationMode: "deterministic",
    disclaimer: result.disclaimer,
    findings,
    summary: summarizeFindings(findings),
  };
}

export function sourceLabel(kind: AssessmentKind): string {
  if (kind === "live") return "Document assessment";
  if (kind === "deterministic") return "Structured review";
  return "Sample results";
}

export function methodLabel(mode: AssessmentRun["evaluationMode"]): string {
  if (mode === "rag") return "Retrieved source passages";
  if (mode === "deterministic") return "Structured rules";
  return "Full document";
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "Not recorded";
  if (ms < 1000) return `${ms} ms`;
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return remainder === 0 ? `${minutes}m` : `${minutes}m ${remainder}s`;
}

export function isReviewApiResult(value: unknown): value is ReviewApiResult {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "string" &&
    record.evaluation_mode === "deterministic" &&
    (record.workspace === "sox" ||
      record.workspace === "project_qa" ||
      record.workspace === "content") &&
    Array.isArray(record.findings)
  );
}

export function isEvaluationApiResult(value: unknown): value is EvaluationApiResult {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "string" &&
    (record.policy_version === "v1" || record.policy_version === "v2") &&
    typeof record.source_document === "string" &&
    Array.isArray(record.findings)
  );
}
