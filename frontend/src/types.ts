export type PolicyVersion = "v1" | "v2";

export type ComplianceStatus =
  | "satisfied"
  | "partial"
  | "missing"
  | "contradicted";

export type WorkspaceId = "security" | "sox" | "project_qa" | "content";

export type ReviewDimension =
  | "design"
  | "completeness"
  | "operating_effectiveness"
  | "artifact_quality"
  | "style";

export type View =
  | "workspaces"
  | "documents"
  | "assessments"
  | "findings"
  | "compare";

export type DocumentKind =
  | "standard"
  | "policy"
  | "control"
  | "evidence"
  | "artifact"
  | "guide"
  | "sample";

export type DatasetDocument = {
  id: string;
  kind: DocumentKind;
  title: string;
  file: string;
  content: string;
  policyVersion?: PolicyVersion;
};

export type Finding = {
  status: ComplianceStatus;
  reason: string;
  evidence: string | null;
};

export type Requirement = {
  id: string;
  title: string;
  category: string;
  categoryLabel: string;
  sourceFile: string;
  fullText: string;
  findings: Record<PolicyVersion, Finding>;
};

export type StatusCounts = Record<ComplianceStatus, number>;

export type AssessmentKind = "sample" | "live" | "deterministic";

export type EvaluationMode = "direct" | "rag";

export type EvaluationState = "completed" | "needs_review" | "failed";

export type EvidenceVerification = "verified" | "missing" | "unverified";

export type DisplayStatus = ComplianceStatus | "needs_review" | "failed";

export type RetrievedPassage = {
  chunk_id: string;
  source_document: string;
  policy_version: PolicyVersion;
  section_number: string;
  section_title: string;
  text: string;
  distance: number | null;
  used_in_finding: boolean;
};

export type FindingView = {
  id: string;
  title: string;
  category: string;
  categoryLabel: string;
  fullText: string;
  classification: ComplianceStatus | null;
  displayStatus: DisplayStatus;
  explanation: string;
  evidence: string | null;
  evidenceVerified: boolean;
  evidenceVerification: EvidenceVerification;
  sourceDocument: string;
  needsReview: boolean;
  evaluationState: EvaluationState;
  uncertaintyNote: string | null;
  retrievedPassages: RetrievedPassage[];
  dimension?: ReviewDimension | null;
  dimensionLabel?: string | null;
};

export type AssessmentSummary = {
  total: number;
  statusCounts: StatusCounts;
  needsReview: number;
  failed: number;
  verifiedQuotes: number;
};

export type AssessmentRun = {
  kind: AssessmentKind;
  workspace: WorkspaceId;
  title: string;
  policyVersion: PolicyVersion | null;
  evaluationId: string | null;
  sourceDocument: string;
  evaluationMode: EvaluationMode | "deterministic";
  requestedMode?: "auto" | EvaluationMode | "deterministic";
  fallbackUsed?: boolean;
  retrievalReady?: boolean | null;
  model?: string | null;
  durationMs?: number | null;
  disclaimer?: string | null;
  findings: FindingView[];
  summary: AssessmentSummary;
};

export type EvaluationApiFinding = {
  requirement_id: string;
  requirement_title: string;
  requirement_text: string;
  category: string;
  classification: ComplianceStatus | null;
  explanation: string;
  supporting_quote: string | null;
  source_document: string;
  evidence_verified: boolean;
  evidence_verification: EvidenceVerification;
  needs_review: boolean;
  evaluation_state: EvaluationState;
  uncertainty_note: string | null;
  retrieved_passages?: RetrievedPassage[];
};

export type EvaluationApiResult = {
  id: string;
  policy_version: PolicyVersion;
  source_document: string;
  evaluation_mode?: EvaluationMode;
  requested_mode?: "auto" | EvaluationMode;
  fallback_used?: boolean;
  retrieval_ready?: boolean | null;
  model?: string | null;
  duration_ms?: number | null;
  findings: EvaluationApiFinding[];
};

export type ReviewApiFinding = {
  id: string;
  title: string;
  category: string;
  dimension: ReviewDimension;
  full_text: string;
  classification: ComplianceStatus;
  explanation: string;
  evidence: string | null;
  source_document: string;
  evidence_verified: boolean;
  evaluation_state: EvaluationState;
  needs_review: boolean;
};

export type ReviewApiResult = {
  id: string;
  workspace: Exclude<WorkspaceId, "security">;
  evaluation_mode: "deterministic";
  disclaimer: string;
  source_document: string;
  findings: ReviewApiFinding[];
};

export type ComplianceDataset = {
  organization: string;
  disclaimer: string;
  counts: Record<PolicyVersion, StatusCounts>;
  documents: DatasetDocument[];
  requirements: Requirement[];
};
